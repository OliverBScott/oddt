from distutils.version import LooseVersion

import rdkit
from rdkit import Chem

from nose.tools import assert_equal, assert_not_equal, assert_almost_equal

import rdkit_fixer


def test_atom_list_to_submol():
    mol = Chem.MolFromSmiles('CCCCC(=O)O')
    submol = rdkit_fixer.AtomListToSubMol(mol, range(3, 7))
    assert_equal(submol.GetNumAtoms(), 4)
    assert_equal(submol.GetNumAtoms(), 4)
    assert_equal(submol.GetNumBonds(), 3)
    assert_equal(submol.GetBondBetweenAtoms(1, 2).GetBondType(),
                 rdkit.Chem.rdchem.BondType.DOUBLE)

    molfile = '2qwe_Sbridge.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)
    assert_equal(mol.GetConformer().Is3D(), True)
    submol = rdkit_fixer.AtomListToSubMol(mol, range(6), includeConformer=True)
    assert_equal(submol.GetConformer().Is3D(), True)

    atom = submol.GetAtomWithIdx(0)
    info = atom.GetPDBResidueInfo()
    assert_equal(info.GetResidueName(), 'CYS')
    assert_equal(info.GetResidueNumber(), 92)

    # test multiple conformers
    mol.AddConformer(mol.GetConformer())
    assert_equal(mol.GetNumConformers(), 2)
    submol = rdkit_fixer.AtomListToSubMol(mol, range(6), includeConformer=True)
    assert_equal(submol.GetNumConformers(), 2)

def test_multivalent_Hs():
    """Test if fixer deals with multivalent Hs"""

    # TODO: require mol without Hs in the future (rdkit v. 2018)
    molfile = '2c92_hypervalentH.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)
    mol = rdkit_fixer.PreparePDBMol(mol, residue_whitelist=[], removeHs=False)

    atom = mol.GetAtomWithIdx(84)
    assert_equal(atom.GetAtomicNum(), 1)  # is it H
    assert_equal(atom.GetDegree(), 1)  # H should have 1 bond

    for n in atom.GetNeighbors():  # Check if neighbor is from the same residue
        assert_equal(atom.GetPDBResidueInfo().GetResidueName(),
                     n.GetPDBResidueInfo().GetResidueName())

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_HOH_bonding():
    """Test if fixer unbinds HOH"""

    molfile = '2vnf_bindedHOH.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)
    # don't use templates and don't remove waters
    mol = rdkit_fixer.PreparePDBMol(mol, residue_whitelist=[], removeHOHs=False)

    atom = mol.GetAtomWithIdx(5)
    assert_equal(atom.GetPDBResidueInfo().GetResidueName(), 'HOH')
    assert_equal(atom.GetDegree(), 0)  # HOH should have no bonds

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_metal_bonding():
    """Test if fixer disconnects metals"""

    molfile = '1ps3_zn.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)

    mol = rdkit_fixer.PreparePDBMol(mol)

    atom = mol.GetAtomWithIdx(36)
    assert_equal(atom.GetAtomicNum(), 30)  # is it Zn
    assert_equal(atom.GetDegree(), 0)  # Zn should have no bonds
    assert_equal(atom.GetFormalCharge(), 2)
    assert_equal(atom.GetNumExplicitHs(), 0)

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_interresidue_bonding():
    """Test if fixer removes wrong connections between residues"""

    molfile = '4e6d_residues.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)

    mol = rdkit_fixer.PreparePDBMol(mol)

    # check if O from PRO
    atom1 = mol.GetAtomWithIdx(11)
    assert_equal(atom1.GetAtomicNum(), 8)
    assert_equal(atom1.GetPDBResidueInfo().GetResidueName(), 'PRO')
    # ...and N from GLN
    atom2 = mol.GetAtomWithIdx(22)
    assert_equal(atom2.GetAtomicNum(), 7)
    assert_equal(atom2.GetPDBResidueInfo().GetResidueName(), 'GLN')
    # ...are not connected
    assert_equal(mol.GetBondBetweenAtoms(11, 22), None)

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_intraresidue_bonding():
    """Test if fixer removes wrong connections within single residue"""

    molfile = '1idg_connectivity.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)
    mol = rdkit_fixer.PreparePDBMol(mol)

    # check if N and C from GLU20 are not connected
    atom1 = mol.GetAtomWithIdx(11)
    assert_equal(atom1.GetAtomicNum(), 7)
    assert_equal(atom1.GetPDBResidueInfo().GetResidueName(), 'GLU')
    assert_equal(atom1.GetPDBResidueInfo().GetResidueNumber(), 20)
    atom2 = mol.GetAtomWithIdx(13)
    assert_equal(atom2.GetAtomicNum(), 6)
    assert_equal(atom2.GetPDBResidueInfo().GetResidueName(), 'GLU')
    assert_equal(atom2.GetPDBResidueInfo().GetResidueNumber(), 20)

    assert_equal(mol.GetBondBetweenAtoms(11, 13), None)

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_bondtype():
    """Test if fixer deals with non-standard residue and fixes bond types"""

    molfile = '3rsb_bondtype.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)
    mol = rdkit_fixer.PreparePDBMol(mol)

    # check if there is double bond between N and C from MSE
    atom1 = mol.GetAtomWithIdx(13)
    assert_equal(atom1.GetAtomicNum(), 6)
    assert_equal(atom1.GetPDBResidueInfo().GetResidueName(), 'MSE')
    atom2 = mol.GetAtomWithIdx(14)
    assert_equal(atom2.GetAtomicNum(), 8)
    assert_equal(atom2.GetPDBResidueInfo().GetResidueName(), 'MSE')

    # there is a bond and it is double
    bond = mol.GetBondBetweenAtoms(13, 14)
    assert_not_equal(bond, None)
    assert_almost_equal(bond.GetBondTypeAsDouble(), 2.0)

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_ring():
    """Test if fixer adds missing bond in ring"""

    molfile = '4yzm_ring.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)
    mol = rdkit_fixer.PreparePDBMol(mol)

    # check if there is double bond between N and C from MSE
    atom1 = mol.GetAtomWithIdx(12)
    assert_equal(atom1.GetAtomicNum(), 6)
    assert_equal(atom1.GetPDBResidueInfo().GetResidueName(), 'PHE')
    atom2 = mol.GetAtomWithIdx(13)
    assert_equal(atom2.GetAtomicNum(), 6)
    assert_equal(atom2.GetPDBResidueInfo().GetResidueName(), 'PHE')

    # there is a bond and it is aromatic
    bond = mol.GetBondBetweenAtoms(12, 13)
    assert_not_equal(bond, None)
    assert_almost_equal(bond.GetBondTypeAsDouble(), 1.5)

    # mol can be sanitized
    assert_equal(int(Chem.SanitizeMol(mol)), 0)


def test_sulphur_bridge():
    """Test sulphur bridges retention"""

    molfile = '2qwe_Sbridge.pdb'
    mol = Chem.MolFromPDBFile(molfile, sanitize=False, removeHs=False)

    mol = rdkit_fixer.PreparePDBMol(mol)

    atom1 = mol.GetAtomWithIdx(5)
    atom2 = mol.GetAtomWithIdx(11)
    bond = mol.GetBondBetweenAtoms(atom1.GetIdx(), atom2.GetIdx())
    assert_equal(atom1.GetPDBResidueInfo().GetName().strip(), 'SG')
    assert_equal(atom1.GetPDBResidueInfo().GetResidueNumber(), 92)
    assert_equal(atom2.GetPDBResidueInfo().GetName().strip(), 'SG')
    assert_equal(atom2.GetPDBResidueInfo().GetResidueNumber(), 417)
    assert_not_equal(bond, None)
