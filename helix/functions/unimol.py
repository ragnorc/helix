from typing import List, Dict, Any
import numpy as np
from helix.core import app, images, volumes
from modal import batched
from loguru import logger

MODEL_DIR = "/mnt/models/unimol"


@app.function(
    image=images.base.pip_install("unimol_tools").env(
        {"UNIMOL_WEIGHT_DIR": MODEL_DIR}),
    gpu='any',
    volumes={MODEL_DIR: volumes.model_weights},
    timeout=3600
)
@batched(max_batch_size=30, wait_ms=1000)
async def compute_batch_unimol_representations(smiles_list: List[str]) -> List[Dict[str, Any]]:
    from unimol_tools import UniMolRepr

    unimol_model = UniMolRepr(data_type='molecule', remove_hs=False)
    unimol_repr = unimol_model.get_repr(smiles_list, return_atomic_reprs=True)

    results = []
    for cls_repr, atomic_repr in zip(unimol_repr['cls_repr'], unimol_repr['atomic_reprs']):
        cls_repr_np = np.array(cls_repr)
        atomic_repr_np = np.array(atomic_repr)
        results.append({
            "cls_repr": cls_repr_np,
            "atomic_reprs": atomic_repr_np,
        })

    return results


@app.function(image=images.base, gpu="any", volumes={MODEL_DIR: volumes.model_weights}, timeout=10000)
def get_unimol_representations(smiles_list: List[str]) -> List[Dict[str, Any]]:
    """
    Get UniMol representations for a list of SMILES strings.

    Args:
        smiles_list (List[str]): List of SMILES strings.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing representations.
    """
    all_representations = list(
        compute_batch_unimol_representations.map(smiles_list, return_exceptions=True))

    logger.info(f"Number of representations: {len(all_representations)}")

    return all_representations


@app.local_entrypoint()
def test():
    # Local entrypoint for testing and development
    test_smiles = ["c1ccc(cc1)C2=NCC(=O)Nc3c2cc(cc3)[N+](=O)[O]"]
    result = get_unimol_representations.remote(test_smiles)

    print("Number of molecules processed:", result["num_molecules"])
    print("CLS token representation shape:",
          result["representations"][0]["cls_repr_shape"])
    print("Atomic level representation shape:",
          result["representations"][0]["atomic_reprs_shape"])
