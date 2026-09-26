import sys, os
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival"); sys.path.insert(0, os.path.dirname(__file__))
import terrain, stubs
if not os.environ.get("REAL"): stubs.install()
sys.argv = [sys.argv[0], "--", "--center", "1050000", "420000", "--radius", "1", "--outdir", os.path.join(os.path.dirname(__file__), "chunks_test")]
import export_chunks; export_chunks.main()
