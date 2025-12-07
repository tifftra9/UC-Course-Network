from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import networkx as nx
import re
import plotly.graph_objects as go
import json
import plotly.utils
import numpy as np
import os
import traceback
import gc

import torch 
from sentence_transformers import util
import boto3

def download_embeddings_from_s3():
    bucket = "uc-course-embeddings"  
    key = "course_embeddings.pt"
    local_path = "/app/course_embeddings.pt"

    if not os.path.exists(local_path):
        print("Downloading embeddings from S3...")
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
        s3.download_file(bucket, key, local_path)
        print("Download complete.")

try:
    download_embeddings_from_s3()
except Exception as e:
    print(f"S3 download failed: {e}")

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

print("Initialize server...")

try:
    cols_to_keep = ['Campus', 'Subject_Code', 'Course_Code', 'Title', 'Prerequisite(s)', 'Course Description']
    df = pd.read_csv('/app/combined_CLEAN.csv', usecols=lambda c: c in cols_to_keep)
    df['Campus'] = df['Campus'].str.upper().str.strip()
    print(f"Loading CSV success {len(df)} lines total")
except Exception as e:
    print(f"Loading CSV fail: {e}")
    df = pd.DataFrame()

try:
    canonical_df = pd.read_csv("/app/canonical_CLEAN.csv")
    canonical_df['Campus'] = canonical_df['Campus'].str.upper().str.strip()
except Exception as e:
    print("Error loading canonical_CLEAN.csv:", e)
    canonical_df = pd.DataFrame()

embeddings = None
try:
    if os.path.exists('/app/course_embeddings.pt'):
        print("Loading Tensor Embeddings...")
        embeddings = torch.load('/app/course_embeddings.pt', map_location=torch.device('cpu'))
        print(f"Loading Embeddings success! Shape: {embeddings.shape}")
    elif os.path.exists('course_embeddings.npy'):
        print("Loading NumPy Embeddings...")
        embeddings = np.load('course_embeddings.npy')
        print(f"Loading Embeddings success! Shape: {embeddings.shape}")
    else:
        print(" Not found embeddings file")
except Exception as e:
    print(f"Loading Embeddings error: {e}")

def normalize_course_id(text):
    if pd.isna(text): return ""
    t = str(text).upper()
    t = re.sub(r"[^A-Z0-9]", "", t)  # removes spaces, hyphens, slashes
    return t

code_to_canonical = {}      # maps (Campus, Course ID) → Canonical_ID
canonical_to_row = {}       # maps Canonical_ID → row dict
canonical_to_codes = {}     # maps Canonical_ID → ["ABC 123", "XYZ 456"]
canonical_index_by_id = {}  # maps Canonical_ID → embedding row index

if not canonical_df.empty:

    canonical_df = canonical_df.reset_index(drop=True)

    for idx, row in canonical_df.iterrows():
        cid = row["Canonical_ID"]

        canonical_index_by_id[cid] = idx
        canonical_to_row[cid] = row.to_dict()
        raw_codes = str(row["Course_Codes"]).split("|")
        cleaned_codes = [normalize_course_id(c) for c in raw_codes]

        canonical_to_codes[cid] = cleaned_codes

        campus = row["Campus"].upper().strip()
        for code in cleaned_codes:
            code_to_canonical[(campus, code)] = cid

if not df.empty:
    df['Course_ID'] = (df['Subject_Code'].fillna('') + df['Course_Code'].fillna('').astype(str)).apply(normalize_course_id)

def parse_prerequisite(prereq_text):
    if not isinstance(prereq_text, str) or not prereq_text.strip(): return []
    text = prereq_text.upper().replace("\xa0", " ").strip()
    text = re.sub(r"\s+[A-D][+-]?\s+OR\s+BETTER", "", text)
    text = re.sub(r"\(", " ( ", text)
    text = re.sub(r"\)", " ) ", text)
    
    def extract_courses(s):
        return re.findall(r'\b[A-Z&]{2,5}\s*\d+[A-Z]*\b', s)

    parts = [p.strip() for p in text.split(';')]
    structure = []

    for part in parts:
        if not part: continue
        courses_in_part = extract_courses(part)
        if not courses_in_part: continue
        
        normalized_courses = [normalize_course_id(c) for c in courses_in_part]
        has_or = ' OR ' in part or 'ONE OF' in part
 
        if has_or:
            if len(normalized_courses) > 1:
                structure.append(normalized_courses)
            else:
                structure.append(normalized_courses)
        else:
            for c in normalized_courses:
                structure.append([c])
    return structure

if not df.empty:
    df['Prereq_Struct'] = df['Prerequisite(s)'].apply(parse_prerequisite)

gc.collect()


graphs = {}
def get_campus_graph(campus_name):
    if campus_name in graphs: return graphs[campus_name]
    
    print(f"构建 {campus_name} 图...")
    campus_df = df[df['Campus'] == campus_name]
    if campus_df.empty: return nx.DiGraph()

    G = nx.DiGraph()
    for _, row in campus_df.iterrows():
        tgt = row['Course_ID']
        G.add_node(tgt, label=tgt, title=row['Title'], group='Course')
        for group in row['Prereq_Struct']:
            if not group: continue
            if len(group) == 1:
                src = group[0]
                if src != tgt:
                    if src not in G: G.add_node(src, label=src, group='External')
                    G.add_edge(src, tgt)
            else:
                or_id = f"OR_{tgt}_{'_'.join(group)}"
                if or_id not in G: G.add_node(or_id, label="OR", size=5, group='Logic')
                G.add_edge(or_id, tgt)
                for src in group:
                    if src != tgt:
                        if src not in G: G.add_node(src, label=src, group='External')
                        G.add_edge(src, or_id)
    graphs[campus_name] = G
    return G


def get_semantic_subgraph(full_graph, root_node, depth=1):

    nodes_to_keep = {root_node}
    current_frontier = {root_node}
    
    for _ in range(depth):
        next_frontier = set()
        for node in current_frontier:
            if node not in full_graph: continue
            preds = list(full_graph.predecessors(node))
            
            for p in preds:
                nodes_to_keep.add(p)
                is_or = str(p).startswith("OR_")
                
                if is_or:
                    grand_preds = list(full_graph.predecessors(p))
                    for gp in grand_preds:
                        nodes_to_keep.add(gp)
                        next_frontier.add(gp)
                else:
                    next_frontier.add(p)
        current_frontier = next_frontier
        if not current_frontier: break
            
    return full_graph.subgraph(list(nodes_to_keep))


def get_optimized_tree_layout(graph, root_node):
    pos = {}
    try:
        rev_G = graph.reverse()
        layers = {}
        lengths = nx.shortest_path_length(rev_G, source=root_node)
        
        for node, length in lengths.items():
            if length not in layers: layers[length] = []
            layers[length].append(node)
        
        pos[root_node] = (0, 0)
        
        for level in sorted(layers.keys()):
            if level == 0: continue
            
            current_nodes = layers[level]
            node_scores = []
            
            for node in current_nodes:
                parents = [p for p in graph.successors(node) if p in pos]
                
                if parents:
                    avg_parent_x = sum(pos[p][0] for p in parents) / len(parents)
                else:
                    avg_parent_x = 0
                
       
                is_or_node = 1 if str(node).startswith("OR_") else 0
                
                node_scores.append({
                    'n': node, 
                    'px': avg_parent_x, 
                    'or': is_or_node, 
                    'name': str(node)
                })
            
            node_scores.sort(key=lambda x: (x['px'], x['or'], x['name']))
            
            sorted_nodes = [x['n'] for x in node_scores]
            width = len(sorted_nodes)
            x_sep = 1.2
            
            for i, n in enumerate(sorted_nodes):
                x = (i - (width - 1) / 2) * x_sep
                y = -level * 1.5 
                pos[n] = (x, y)
                
        return pos
    except Exception as e:
        print(f"Layout Error: {e}")
        return nx.spring_layout(graph, seed=42)

def create_plotly_json(G, title, highlight):
    if len(G.nodes) == 0: return None
    try:
        pos = get_optimized_tree_layout(G, highlight)
        
        direct, indirect = set(), set()
        if highlight in G:
            for p in G.predecessors(highlight):
                if G.nodes[p].get('group') == 'Logic':
                    indirect.update(G.predecessors(p))
                else:
                    direct.add(p)

        valid_subjects = set(df['Subject_Code'].dropna().unique())

        edge_x, edge_y = [], []
        for u, v in G.edges():
            if u in pos and v in pos:
                edge_x.extend([pos[u][0], pos[v][0], None])
                edge_y.extend([pos[u][1], pos[v][1], None])
        
        node_x, node_y, txt, color, size, ids = [], [], [], [], [], []
        for n in G.nodes():
            if n not in pos: continue
            node_x.append(pos[n][0])
            node_y.append(pos[n][1])
            ids.append(n)
            
            node_group = G.nodes[n].get('group', 'External')
            
            c, s = '#adb5bd', 12 
            hover_prefix = "External"
            
            if n == highlight: 
                c, s = '#FFD700', 40 
                hover_prefix = "TARGET"
            elif n in direct: 
                c, s = '#FFA500', 25 
                hover_prefix = "Direct Prereq"
            elif n in indirect: 
                c, s = '#FF4500', 25
                hover_prefix = "OR-Option"
            elif str(n).startswith("OR_"): 
                c, s = '#ff6b6b', 8
                hover_prefix = "Logic (OR)"
            elif node_group == 'Course': 
                c, s = '#4dabf7', 15 
                hover_prefix = "Course"
            else:
                match = re.match(r'^([A-Z&]+)', str(n))
                if match:
                    subject_part = match.group(1)
                    if subject_part in valid_subjects:
                        c, s = '#343a40', 12
                        hover_prefix = "Discontinued/Legacy"
            
            color.append(c); size.append(s)
            
            node_title = G.nodes[n].get('title', '')
            if str(n).startswith("OR_"):
                txt.append("")   
            else:
                if node_title:
                    txt.append(f"<b>{hover_prefix}: {n}</b><br>{node_title}")
                else:
                    txt.append(f"<b>{hover_prefix}: {n}</b>")

        fig = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='#ccc', width=0.8), hoverinfo='none'),
            go.Scatter(x=node_x, y=node_y, mode='markers', marker=dict(color=color, size=size), hovertext=txt, hoverinfo='text', customdata=ids)
        ], layout=go.Layout(
            title={'text': title, 'x':0.5, 'font':{'size':16}}, showlegend=False, hovermode='closest',
            margin=dict(t=40,b=20,l=5,r=5), xaxis=dict(visible=False), yaxis=dict(visible=False), clickmode='event+select'
        ))
        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    except Exception as e:
        print(f"绘图错误: {e}")
        return None


@app.route('/')
def home():
    return "API Running"

@app.route('/api/search', methods=['GET'])
def search():
    try:
        campus = request.args.get('campus', 'UCD').upper()
        cid = normalize_course_id(request.args.get('course_id', ''))
        
        try:
            depth = int(request.args.get('depth', 1)) 
        except:
            depth = 1

        rows = df[(df['Campus'] == campus) & (df['Course_ID'] == cid)]
        if rows.empty:
            return jsonify({"error": f"Course {cid} not found in {campus}"}), 404
        
        prereq_text = rows.iloc[0]['Prerequisite(s)']
        
        resp = {
            "prereq_list": prereq_text if pd.notna(prereq_text) else "None",
            "graph": None,
            "similarity": {},
            "canonical": None
        }
        
        current_graph = get_campus_graph(campus)
        if cid in current_graph:
            sub_G = get_semantic_subgraph(current_graph, cid, depth=depth)
            resp['graph'] = create_plotly_json(sub_G, f"Tree: {cid} (Depth {depth})", cid)
        
        key = (campus, cid)
        canon_id = code_to_canonical.get(key)

        print("==== DEBUG CANONICAL LOOKUP ====")
        print("Campus:", campus)
        print("CID:", cid)
        print("Lookup Key:", key)
        print("Canon ID:", canon_id)
        print("Embeddings Loaded:", embeddings is not None)
        print("Canonical Index Size:", len(canonical_index_by_id))
        print("Canonical DF Size:", len(canonical_df))
        print("Code to Canonical Size:", len(code_to_canonical))
        print("================================")


        if (embeddings is not None and canon_id in canonical_index_by_id):
            canon_idx = canonical_index_by_id[canon_id]
            target_emb = embeddings[canon_idx].unsqueeze(0)

            resp["canonical"] = {
                "canonical_id": canon_id,
                "subjects": canonical_to_row[canon_id].get("Subject", ""),
                "codes": canonical_to_codes[canon_id],
                "title": canonical_to_row[canon_id]["Title"],
                "description": canonical_to_row[canon_id]["Course Description"],
                "prerequisites": prereq_text if pd.notna(prereq_text) else "None"
            }
            
            sim_res = {}

            for c in ["UCD", "UCLA", "UCSC", "UCI"]:
                if c == campus:
                    sim_res[c] = []
                    continue

                campus_mask = canonical_df["Campus"] == c
                if not campus_mask.any():
                    sim_res[c] = []
                    continue

                campus_embs = embeddings[campus_mask.values]
                campus_canon_ids = canonical_df.loc[campus_mask, "Canonical_ID"].tolist()

                hits = util.semantic_search(target_emb, campus_embs, top_k=5)[0]

                campus_hits = []
                for h in hits:
                    hit_id = campus_canon_ids[h["corpus_id"]]
                    hit_row = canonical_to_row[hit_id]

                    campus_hits.append({
                        "canonical_id": hit_id,
                        "codes": canonical_to_codes[hit_id],
                        "title": hit_row["Title"],
                        "score": round(h["score"], 3)
                    })

                sim_res[c] = campus_hits

            resp["similarity"] = sim_res
            
        return jsonify(resp)

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7860)
