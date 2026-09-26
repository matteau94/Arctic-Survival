import sys, os, bpy, cProfile, pstats
sys.path.insert(0, r"C:\Users\leosp\Documents\Blender\Artic-Survival"); sys.path.insert(0, os.path.dirname(__file__))
import terrain, stubs; stubs.install()
from terrain import streaming as S
ctx,m,n=S.sample_chunk(40,16,0); S.build_terrain_mesh("w",ctx,m,n)
cProfile.run('S.build_terrain_mesh("x",ctx,m,n)', 'p.out')
pstats.Stats('p.out').sort_stats('tottime').print_stats(8)
