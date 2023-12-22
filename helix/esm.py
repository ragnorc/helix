from io import StringIO
from modal import Image, method, Mount
from .main import CACHE_DIR, volume, stub
from Bio.SeqRecord import SeqRecord
from Bio.PDB.Structure import Structure
from Bio import SeqIO
from Bio.PDB.PDBIO import PDBIO
import os
import transformers


def download_models():
    from transformers import EsmModel, EsmForProteinFolding
    EsmForProteinFolding.from_pretrained(
        "facebook/esmfold_v1")
    EsmModel.from_pretrained(
        "facebook/esm2_t36_3B_UR50D")
    # tokenizers
    transformers.AutoTokenizer.from_pretrained(
        "facebook/esmfold_v1")
    transformers.AutoTokenizer.from_pretrained(
        "facebook/esm2_t36_3B_UR50D")


dockerhub_image = Image.from_registry(
    "pytorch/pytorch:1.12.1-cuda11.3-cudnn8-devel"
).apt_install("git"
              ).pip_install("fair-esm[esmfold]",
                            "dllogger @ git+https://github.com/NVIDIA/dllogger.git",
                            "openfold @ git+https://github.com/aqlaboratory/openfold.git@4b41059694619831a7db195b7e0988fc4ff3a307"
                            ).pip_install("gradio",
                                          "biopython",
                                          "pandas",
                                          "transformers",
                                          "scikit-learn",
                                          "matplotlib",
                                          "seaborn",
                                          ).run_function(download_models, mounts=[Mount.from_local_python_packages("helix")])


@stub.cls(gpu='A10G', timeout=2000, network_file_systems={CACHE_DIR: volume}, image=dockerhub_image, allow_cross_region_volumes=True, concurrency_limit=9)
class EsmModel():
    def __init__(self, device: str = "cuda", model_name: str = "facebook/esm2_t36_3B_UR50D"):
        import transformers
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_name)
        self.model = transformers.AutoModel.from_pretrained(
            model_name)
        self.device = device
        if device == "cuda":
            self.model = self.model.cuda()
        self.model.eval()

    @method()
    def infer(self, sequences, output_hidden_states: bool = False, output_attentions: bool = False) -> transformers.modeling_outputs.BaseModelOutputWithPoolingAndCrossAttentions:
        import torch
        if not torch.cuda.is_available():
            raise Exception("CUDA is not available")
        print(f"Running inference on {sequences} sequences")
        sequences = [str(sequence.seq) for sequence in sequences]
        tokenized = self.tokenizer(
            sequences, return_tensors="pt", add_special_tokens=False)['input_ids']
        tokenized = tokenized.to(self.device)
        with torch.inference_mode():
            outputs = self.model(tokenized, output_hidden_states=output_hidden_states,
                                 output_attentions=output_attentions)
        return outputs

    def __exit__(self, exc_type, exc_value, traceback):
        import torch
        torch.cuda.empty_cache()


@stub.cls(gpu='A10G', timeout=2000, network_file_systems={CACHE_DIR: volume}, image=dockerhub_image, allow_cross_region_volumes=True, concurrency_limit=9)
class EsmForMaskedLM():
    def __init__(self, device: str = "cuda", model_name: str = "facebook/esm2_t36_3B_UR50D"):
        import transformers
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            model_name)
        self.model = transformers.AutoModelForMaskedLM.from_pretrained(
            model_name)
        self.device = device
        if device == "cuda":
            self.model = self.model.cuda()
        self.model.eval()

    @method()
    def perplexity(self, sequence: str, batch_size: int = 32) -> float:
        import torch
        import numpy as np
        tokenized = self.tokenizer.encode(sequence, return_tensors='pt')
        repeat_input = tokenized.repeat(tokenized.size(-1)-2, 1)

        # mask one by one except [CLS] and [SEP]
        mask = torch.ones(tokenized.size(-1) - 1).diag(1)[:-2]
        masked_input = repeat_input.masked_fill(
            mask == 1, self.tokenizer.mask_token_id)

        labels = repeat_input.masked_fill(
            masked_input != self.tokenizer.mask_token_id, -100)

        # Initialize loss accumulator
        total_loss = 0.0

        # Process in batches
        for i in range(0, masked_input.size(0), batch_size):
            batch_masked_input = masked_input[i:i+batch_size].to(self.device)
            batch_labels = labels[i:i+batch_size].to(self.device)

            with torch.inference_mode():
                outputs = self.model(batch_masked_input, labels=batch_labels)
                loss = outputs.loss
                total_loss += loss.item() * batch_masked_input.size(0)

        # Calculate average loss
        avg_loss = total_loss / masked_input.size(0)

        return np.exp(avg_loss)

    def __exit__(self, exc_type, exc_value, traceback):
        import torch
        torch.cuda.empty_cache()


@stub.cls(gpu='A10G', timeout=2000, network_file_systems={CACHE_DIR: volume}, image=dockerhub_image)
class ESMFold():
    def __init__(self, device: str = "cuda"):
        from transformers import AutoTokenizer, EsmForProteinFolding
        self.tokenizer = AutoTokenizer.from_pretrained("facebook/esmfold_v1")
        self.model = EsmForProteinFolding.from_pretrained(
            "facebook/esmfold_v1",)  # low_cpu_mem_usage=True
        self.device = device
        if device == "cuda":
            self.model = self.model.cuda()
        self.model.eval()
        # TODO: Make chunk size configurable?
        self.model.trunk.set_chunk_size(64)

    @method()
    def infer(self, sequence: SeqRecord) -> Structure:
        import torch
        tokenized = self.tokenizer(
            [str(sequence.seq)], return_tensors="pt", add_special_tokens=False)['input_ids']
        tokenized = tokenized.to(self.device)
        with torch.inference_mode():
            outputs = self.model(tokenized)
        pdb_structures = self.convert_outputs_to_pdb(outputs)
        # Convert pdb strings to biopython structures
        from Bio.PDB import PDBParser
        parser = PDBParser()
        structures = [parser.get_structure(
            sequence.id, StringIO(pdb)) for pdb in pdb_structures]
        return structures[0]

    @staticmethod
    def convert_outputs_to_pdb(outputs):
        from transformers.models.esm.openfold_utils.protein import to_pdb, Protein as OFProtein
        from transformers.models.esm.openfold_utils.feats import atom14_to_atom37
        final_atom_positions = atom14_to_atom37(
            outputs["positions"][-1], outputs)
        outputs = {k: v.to("cpu").numpy() for k, v in outputs.items()}
        final_atom_positions = final_atom_positions.cpu().numpy()
        final_atom_mask = outputs["atom37_atom_exists"]
        pdbs = []
        for i in range(outputs["aatype"].shape[0]):
            aa = outputs["aatype"][i]
            pred_pos = final_atom_positions[i]
            mask = final_atom_mask[i]
            resid = outputs["residue_index"][i] + 1
            pred = OFProtein(
                aatype=aa,
                atom_positions=pred_pos,
                atom_mask=mask,
                residue_index=resid,
                b_factors=outputs["plddt"][i],
                chain_index=outputs["chain_index"][i] if "chain_index" in outputs else None,
            )
            pdbs.append(to_pdb(pred))
        return pdbs


PROTEIN_STRUCTURE_MODELS = {
    "esmfold": ESMFold
}


@stub.function(network_file_systems={CACHE_DIR: volume}, image=dockerhub_image)
def predict_structures(sequences, model_name: str = "esmfold"):
    if model_name not in PROTEIN_STRUCTURE_MODELS:
        raise ValueError(
            f"Model {model_name} is not supported. Supported models are: {list(PROTEIN_STRUCTURE_MODELS.keys())}")
    print(f"Using model {model_name}")
    print(f"Predicting structures for {len(sequences)} sequences")
    model = PROTEIN_STRUCTURE_MODELS[model_name]()

    result = []
    for struct in model.infer.map(sequences, return_exceptions=True):
        if isinstance(struct, Exception):
            print(f"Error: {struct}")
        else:
            print(f"Successfully predicted structure for {struct.id}")
            result.append(struct)
    return result


@stub.local_entrypoint()
def predict_structures_from_fasta(fasta_file: str, output_dir: str):
    sequences = list(SeqIO.parse(fasta_file, "fasta"))
    result = predict_structures.remote(sequences)
    os.makedirs(output_dir, exist_ok=True)
    for struct in result:
        io = PDBIO()
        io.set_structure(struct)
        io.save(f"{output_dir}/{struct.id}.pdb")
