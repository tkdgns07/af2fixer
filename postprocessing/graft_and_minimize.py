#!/usr/bin/env python
import argparse, os, tempfile
from typing import List, Tuple
import gemmi as gm
from simtk import unit
from simtk.openmm import app
import openmm as mm

def parse_map(map_str: str) -> List[Tuple[str, int, int, int, int]]:
    out = []
    for token in map_str.split(','):
        token = token.strip()
        if not token: continue
        left, right = token.split('=')
        chain, tspan = left.split(':')
        t_a, t_b = [int(x) for x in tspan.split('-')]
        p_a, p_b = [int(x) for x in right.split('-')]
        out.append((chain, t_a, t_b, p_a, p_b))
    return out

def graft(template: gm.Structure, predicted: gm.Structure, mapping):
    p_model = predicted[0]
    t_model = template[0]
    pred_residues = []
    for ch in p_model:
        for res in ch:
            if res.is_polymer():
                pred_residues.append(res)
    for chain_name, t_a, t_b, p_a, p_b in mapping:
        t_chain = t_model[chain_name]
        length_t = t_b - t_a + 1
        length_p = p_b - p_a + 1
        if length_t != length_p:
            raise ValueError(f"Length mismatch for {chain_name}: template {length_t} vs predicted {length_p}")
        for i in range(length_t):
            t_resnum = t_a + i
            p_index = p_a + i
            if not (1 <= p_index <= len(pred_residues)):
                raise IndexError(f"Pred index {p_index} out of range (1..{len(pred_residues)})")
            p_res = pred_residues[p_index - 1]
            t_res = None
            for r in t_chain:
                if r.seqid.num == t_resnum and r.is_polymer():
                    t_res = r; break
            if t_res is None:
                raise KeyError(f"Template residue {chain_name}:{t_resnum} not found")
            p_atoms_by_name = {a.name.strip(): a for a in p_res}
            for t_atom in t_res:
                nm = t_atom.name.strip()
                if nm in p_atoms_by_name:
                    t_atom.pos = p_atoms_by_name[nm].pos

def write_pdb(struct: gm.Structure, path: str):
    with gm.PdbWriter(path) as w:
        w.write_structure(struct)

def minimize_pdb(in_pdb: str, out_pdb: str, platform: str = 'CPU'):
    pdb = app.PDBFile(in_pdb)
    modeller = app.Modeller(pdb.topology, pdb.positions)
    ff = app.ForceField('amber14-all.xml', 'amber14/tip3pfb.xml')
    modeller.addHydrogens(forcefield=ff, pH=7.0)
    system = ff.createSystem(modeller.topology, nonbondedMethod=app.NoCutoff, constraints=app.HBonds)
    integrator = mm.LangevinIntegrator(300*unit.kelvin, 1.0/unit.picosecond, 0.004*unit.picoseconds)
    plat = mm.Platform.getPlatformByName(platform) if platform in [p.name for p in [mm.Platform.getPlatform(0)] * mm.Platform.getNumPlatforms()] else mm.Platform.getPlatformByName('CPU')
    sim = app.Simulation(modeller.topology, system, integrator, plat)
    sim.context.setPositions(modeller.positions)
    mm.LocalEnergyMinimizer.minimize(sim.context, maxIterations=500)
    state = sim.context.getState(getPositions=True)
    app.PDBFile.writeFile(modeller.topology, state.getPositions(), open(out_pdb, 'w'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--template', required=True)
    ap.add_argument('--pred', required=True)
    ap.add_argument('--output', required=True)
    ap.add_argument('--map', required=True, help='A:100-130=1-31[,B:..=..]')
    ap.add_argument('--minimize', action='store_true')
    ap.add_argument('--platform', default='CPU')
    args = ap.parse_args()

    template = gm.read_structure(args.template)
    predicted = gm.read_structure(args.pred)
    mapping = parse_map(args.map)
    graft(template, predicted, mapping)

    with tempfile.TemporaryDirectory() as td:
        grafted_pdb = os.path.join(td, 'grafted.pdb')
        write_pdb(template, grafted_pdb)
        if args.minimize:
            minimize_pdb(grafted_pdb, args.output, platform=args.platform)
        else:
            from shutil import copyfile; copyfile(grafted_pdb, args.output)
    print(f"[OK] Wrote {args.output}")

if __name__ == '__main__':
    main()
