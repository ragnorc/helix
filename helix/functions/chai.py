import helix.core.images as images
from modal import method, gpu
from helix.core import app, volumes
import numpy as np
from typing import List, Dict, Any
from pathlib import Path
import tempfile
import os

MODEL_DIR = "/mnt/models"

chai_image = images.base.pip_install("chai_lab").env(
    {"CHAI_DOWNLOADS_DIR": MODEL_DIR})


@app.cls(gpu=gpu.A100(), timeout=6000, image=chai_image, volumes={MODEL_DIR: volumes.model_weights})
class ChaiPredictor:
    def __init__(self, device: str = "cuda"):
        import torch
        from chai_lab.chai1 import run_inference
        self.run_inference = run_inference
        self.device = torch.device(device)

    @method()
    def predict_structure(self, sequence: str, inference_params: Dict[str, Any]) -> str:
        fasta_content = self.create_fasta_content(sequence)

        with tempfile.NamedTemporaryFile(mode='w+', suffix='.fasta', delete=False) as temp_fasta:
            temp_fasta.write(fasta_content)
            temp_fasta_path = temp_fasta.name

        try:
            fasta_file = Path(temp_fasta_path)

            with tempfile.TemporaryDirectory() as temp_output_dir:
                output_dir = Path(temp_output_dir)

                candidates = self.run_inference(
                    fasta_file=fasta_file,
                    output_dir=output_dir,
                    device=self.device,
                    **inference_params
                )

                best_index = np.argmax(candidates.plddt.mean(axis=1))
                best_cif_path = candidates.cif_paths[best_index]

                with open(best_cif_path, 'r') as cif_file:
                    best_structure = cif_file.read()

                return best_structure

        finally:
            os.unlink(temp_fasta_path)

    @staticmethod
    def create_fasta_content(sequence: str) -> str:
        return f">protein\n{sequence}"


@app.function(image=images.base, timeout=10000)
def predict_structures_batch(sequences: List[str], inference_params: Dict[str, Any]):
    print(f"Predicting structures for {len(sequences)} sequences")
    predictor = ChaiPredictor()

    args_list = [(seq, inference_params) for seq in sequences]
    return list(predictor.predict_structure.starmap(args_list))
