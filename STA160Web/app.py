from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import networkx as nx
import re
import plotly.graph_objects as go
import json
import plotly.utils
from sentence_transformers import util
import torch
import os
import traceback
import gc

app = Flask(__name__)
CORS(app)


try:
    cols_to_keep = ['Campus', 'Subject_Code', 'Course_Code', 'Title', 'Prerequisite(s)']
    df = pd.read_csv('combined_CLEAN.csv', usecols=lambda c: c in cols_to_keep or c == 'Course Description')
    df['Campus'] = df['Campus'].str.upper().str.strip()
except Exception as e:
    df = pd.DataFrame()

try:
    canonical_df = pd.read_csv('canonical_CLEAN.csv')
    canonical_df['Campus'] = canonical_df['Campus'].str.upper().str.strip()
except Exception as e:
    canonical_df = pd.DataFrame()

embeddings = None
try:
    if os.path.exists('final_course_embeddings.pt'):
        print("loading Embeddings...")
        embeddings = torch.load('final_course_embeddings.pt', map_location=torch.device('cpu'))
        print(f"Loading Embeddings sucess! Shape: {embeddings.shape}")
    else:
        print("Not found embeddings")
except Exception as e:
    print(f"Embeddings loading error: {e}")

def normalize_course_id(text):
    if pd.isna(text): return ""
    return str(text).replace(" ", "").upper()

if not df.empty:
    df['Course_ID'] = (df['Subject_Code'].fillna('') + df['Course_Code'].fillna('').astype(str)).apply(normalize_course_id)

code_to_canonical = {} # (Campus, Code) -> Canonical ID
canonical_to_row = {} # Canonical ID -> row information
canonical_to_codes = {} # Canonical ID -> split cross-listed codes
canonical_index_by_id = {} 

if not canonical_df.empty:
    for idx, row in canonical_df.iterrows():
        canon_id = int(row["Canonical_ID"]) 

        canonical_index_by_id[canon_id] = idx
        canonical_to_row[canon_id] = row.to_dict() # Canonical ID -> row information

        raw_codes = str(row["Course_Codes"]).split("|") # Canonical ID -> split cross-listed codes
        cleaned_codes = [normalize_course_id(c) for c in raw_codes]
        canonical_to_codes[canon_id] = cleaned_codes
        
        campus = row["Campus"] # (Campus, Code) -> Canonical ID
        for code in cleaned_codes:
            code_to_canonical[(campus, code)] = canon_id

def parse_prerequisite(prereq_text):
    if not isinstance(prereq_text, str) or not prereq_text.strip(): return []
    clean_text = prereq_text.replace("\xa0", " ")
    and_parts = [p.strip() for p in clean_text.split(";")]
    structure = []
    for part in and_parts:
        raw_courses = re.findall(r'\b[A-Z&]{2,5}\s*\d+[A-Z]*\b', part)
        if not raw_courses: continue
        courses = [normalize_course_id(c) for c in raw_courses]
        if '(' in part and ')' in part or ' or ' in part.lower():
            if len(courses) > 1: structure.append(courses)
        else:
            for c in courses: structure.append([c])
    return structure

if not df.empty:
    df['Prereq_Struct'] = df['Prerequisite(s)'].apply(parse_prerequisite)

gc.collect()


graphs = {}

def get_campus_graph(campus_name):

    if campus_name in graphs:
        return graphs[campus_name]
    
    campus_df = df[df['Campus'] == campus_name]
    
    if campus_df.empty:
        return nx.DiGraph()

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

def get_optimized_tree_layout(graph, root_node):
    pos = {}
    try:
        layers = {}
        rev_G = graph.reverse()
        lengths = nx.shortest_path_length(rev_G, source=root_node)
        for node, length in lengths.items():
            if length not in layers: layers[length] = []
            layers[length].append(node)
        
        pos[root_node] = (0, 0)
        for level in sorted(layers.keys()):
            if level == 0: continue
            node_scores = []
            for node in layers[level]:
                parents = [p for p in graph.successors(node) if p in pos]
                avg_x = sum(pos[p][0] for p in parents)/len(parents) if parents else 0
                is_or = 1 if str(node).startswith("OR_") else 0
                node_scores.append({'n': node, 'px': avg_x, 'or': is_or, 'name': str(node)})
            
            node_scores.sort(key=lambda x: (x['px'], x['or'], x['name']))
            nodes = [x['n'] for x in node_scores]
            width = len(nodes)
            for i, n in enumerate(nodes):
                pos[n] = ((i - (width-1)/2)*1.2, -level*1.5)
        return pos
    except Exception:
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
            
            c, s = '#adb5bd', 12
            if n == highlight: c, s = '#FFD700', 40
            elif n in direct: c, s = '#FFA500', 25
            elif n in indirect: c, s = '#FF4500', 25
            elif str(n).startswith("OR_"): c, s = '#ff6b6b', 8
            elif G.nodes[n].get('group') == 'Course': c, s = '#4dabf7', 15
            
            color.append(c); size.append(s)
            txt.append(f"<b>{n}</b><br>{G.nodes[n].get('title', '')}")

        fig = go.Figure(data=[
            go.Scatter(x=edge_x, y=edge_y, mode='lines', line=dict(color='#ccc', width=0.8), hoverinfo='none'),
            go.Scatter(x=node_x, y=node_y, mode='markers', marker=dict(color=color, size=size), hovertext=txt, hoverinfo='text', customdata=ids)
        ], layout=go.Layout(
            title={'text': title, 'x':0.5, 'font':{'size':16}}, showlegend=False, hovermode='closest',
            margin=dict(t=40,b=20,l=5,r=5), xaxis=dict(visible=False), yaxis=dict(visible=False), clickmode='event+select'
        ))
        return json.loads(json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder))
    except Exception as e:
        return None


@app.route('/')
def home():
    return "API Optimized (Memory Safe) is Running!"

@app.route('/api/search', methods=['GET'])
def search():
    try:
        campus = request.args.get('campus', 'UCD').upper()
        cid = normalize_course_id(request.args.get('course_id', ''))
        
        rows = df[(df['Campus'] == campus) & (df['Course_ID'] == cid)]
        if rows.empty:
            return jsonify({"error": f"Course {cid} not found in {campus}"}), 404
        
        prereq_text = rows.iloc[0]['Prerequisite(s)']
        
        resp = {
            "prereq_list": prereq_text if pd.notna(prereq_text) else "None",
            "graph": None,
            "canonical": None,
            "similarity": {}
        }
        
        current_graph = get_campus_graph(campus)
        
        if cid in current_graph:
            anc = nx.ancestors(current_graph, cid)
            sub = current_graph.subgraph(anc.union({cid}))
            resp['graph'] = create_plotly_json(sub, f"Tree: {cid}", cid)
        
        key = (campus, cid)
        canon_id = code_to_canonical.get(key)
        
        if (embeddings is not None and canon_id in canonical_index_by_id):
            canon_idx = canonical_index_by_id[canon_id]
            target_emb = embeddings[canon_idx].unsqueeze(0)

            resp["canonical"] = {
                "canonical_id": canon_id,
                "codes": canonical_to_codes[canon_id],
                "subjects": canonical_to_row[canon_id]["Subject"].split("|"),
                "title": canonical_to_row[canon_id]["Title"],
                "description": canonical_to_row[canon_id]["Course Description"]
            }

            sim_res = {}
            for c in ['UCD', 'UCLA', 'UCSC', 'UCI']:
                if c == campus: 
                    sim_res[c] = []
                    continue
                
                mask = (canonical_df['Campus'] == c)
                if not mask.any(): 
                    sim_res[c] = []
                    continue
                
                c_embs = embeddings[mask.values] 
                c_ids  = canonical_df.loc[mask, "Canonical_ID"].tolist()
                
                hits = util.semantic_search(target_emb, c_embs, top_k=5)[0]
                
                campus_hits = []
                for h in hits:
                    hit_canon_id = c_ids[h["corpus_id"]]
                    hit_row = canonical_to_row[hit_canon_id]

                    campus_hits.append({
                        "canonical_id": hit_canon_id,
                        "codes": canonical_to_codes[hit_canon_id],
                        "title": hit_row["Title"],
                        "score": round(h["score"], 3)
                    })

                sim_res[c] = campus_hits

            resp['similarity'] = sim_res
            
        return jsonify(resp)

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
