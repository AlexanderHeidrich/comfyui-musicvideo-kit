#!/usr/bin/env python3
"""Queue every scene of a song through ComfyUI's HTTP API - one job per scene.

  queue_comfy.py <song-dir> <workflow_api.json> [--variant v1] [--dry-run]

Export the graph from ComfyUI with Workflow -> Export (API), not the normal save,
and title the nodes you want driven: PROMPT, AUDIO, LENGTH. This substitutes each
scene's prompt text, audio path and frame count into them and POSTs to /prompt.
Stdlib only. Run --dry-run first: it also reports which nodes it matched.

env: COMFY_HOST (default http://127.0.0.1:8188)
"""
import argparse, csv, json, os, sys, urllib.error, urllib.request

HOST = os.environ.get("COMFY_HOST", "http://127.0.0.1:8188")
# the field each node type takes its value in, longest-match first
PROMPT_KEYS = ("prompt", "text", "string", "value")
AUDIO_KEYS = ("audio", "audio_file", "path", "file", "value")
LENGTH_KEYS = ("length", "frames", "value", "int")


def find_node(graph, title, keys):
    """-> (node_id, input_name) for the node titled `title`"""
    hits = [(nid, n) for nid, n in graph.items()
            if (n.get("_meta", {}).get("title") or "").strip().lower() == title.lower()]
    if not hits:
        return None, None
    if len(hits) > 1:
        sys.exit("more than one node is titled '%s' - titles must be unique" % title)
    nid, node = hits[0]
    for k in keys:
        if k in node.get("inputs", {}) and not isinstance(node["inputs"][k], list):
            return nid, k
    ins = ", ".join(node.get("inputs", {})) or "(none)"
    sys.exit("node '%s' (%s) has no settable field among %s - it has: %s"
             % (title, node.get("class_type"), "/".join(keys), ins))


def parse_range(spec, present):
    """no spec means every scene the manifest actually lists - scene numbers are
    not 1..n: 00 is the Vorspann and 90+ are compositing elements"""
    if not spec:
        return set(present)
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("song")
    ap.add_argument("workflow")
    ap.add_argument("--variant", default="v1")
    ap.add_argument("--scenes", help="subset, e.g. 1-10,15")
    ap.add_argument("--host", default=HOST)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--title-prompt", default="PROMPT")
    ap.add_argument("--title-audio", default="AUDIO")
    ap.add_argument("--title-length", default="LENGTH")
    a = ap.parse_args()

    song = a.song.rstrip("/")
    graph = json.load(open(a.workflow, encoding="utf-8"))
    if "nodes" in graph and "last_node_id" in graph:
        sys.exit("that is a UI workflow, not the API format.\n"
                 "In ComfyUI: Workflow -> Export (API).")

    p_id, p_key = find_node(graph, a.title_prompt, PROMPT_KEYS)
    au_id, au_key = find_node(graph, a.title_audio, AUDIO_KEYS)
    ln_id, ln_key = find_node(graph, a.title_length, LENGTH_KEYS)
    if not p_id:
        sys.exit("no node titled '%s'. Double-click a node's title bar to rename it."
                 % a.title_prompt)
    print("prompt -> node %s.%s (%s)" % (p_id, p_key, graph[p_id]["class_type"]))
    print("audio  -> %s" % ("node %s.%s (%s)" % (au_id, au_key, graph[au_id]["class_type"])
                            if au_id else "NOT FOUND - audio will not be set"))
    print("length -> %s" % ("node %s.%s (%s)" % (ln_id, ln_key, graph[ln_id]["class_type"])
                            if ln_id else "NOT FOUND - length will not be set"))

    rows = list(csv.DictReader(open(os.path.join(song, "__SCENES.tsv"),
                                   encoding="utf-8"), delimiter="\t"))
    wanted = parse_range(a.scenes, [int(r["scene"]) for r in rows])
    queued = 0
    for r in rows:
        n = int(r["scene"])
        if n not in wanted:
            continue
        pf = [f for f in r["prompts"].split() if f.endswith("-%s.txt" % a.variant)]
        if not pf:
            print("! scene %02d has no %s variant" % (n, a.variant)); continue
        text = open(os.path.join(song, pf[0]), encoding="utf-8").read()
        graph[p_id]["inputs"][p_key] = text
        mute = (r.get("audio") or "-").strip() in ("", "-")
        if au_id and not mute:
            graph[au_id]["inputs"][au_key] = os.path.abspath(
                os.path.join(song, r["audio"]))
        if ln_id:
            graph[ln_id]["inputs"][ln_key] = int(r["frames"])

        if a.dry_run:
            print("  scene %02d  %-4s frames  %-34s %d chars of prompt"
                  % (n, r["frames"], "(no audio)" if mute else r["audio"], len(text)))
            queued += 1
            continue
        body = json.dumps({"prompt": graph}).encode()
        req = urllib.request.Request(a.host.rstrip("/") + "/prompt", data=body,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                got = json.load(resp)
            print("  scene %02d queued  %s" % (n, got.get("prompt_id", "?")))
            queued += 1
        except urllib.error.HTTPError as e:
            sys.exit("scene %02d rejected by ComfyUI (%s):\n%s"
                     % (n, e.code, e.read().decode(errors="replace")[:800]))
        except urllib.error.URLError as e:
            sys.exit("cannot reach ComfyUI at %s (%s)" % (a.host, e))

    print("%s %d job(s)%s" % ("would queue" if a.dry_run else "queued", queued,
                              " - variant %s" % a.variant))


if __name__ == "__main__":
    main()
