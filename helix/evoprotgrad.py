import hashlib
from pprint import pprint
from modal import Image, method
import pandas as pd
from .main import stub

image = Image.debian_slim().pip_install(
    "transformers[torch]==4.30.0",
    "torch",
    "evo_prot_grad",
    "pandas")


@stub.cls(gpu='any', timeout=2000, image=image, allow_cross_region_volumes=True, concurrency_limit=9)
class EvoProtGrad:
    def __init__(self, experts: list[str] = ["esm"], device: str = "cuda"):
        from evo_prot_grad import get_expert
        self.experts = [get_expert(
            expert_name=expert, temperature=1.0, device=device) for expert in experts]

    @method()
    def evolve(self, sequence: str, n_steps: int = 100, parallel_chains: int = 10, max_mutations: int = -1, random_seed: int = None):
        from evo_prot_grad import DirectedEvolution

        variants, scores = DirectedEvolution(wt_protein=sequence, experts=self.experts, n_steps=n_steps,
                                             parallel_chains=parallel_chains, max_mutations=max_mutations, random_seed=random_seed, output="best")()
        variants = [variant.replace(' ', '') for variant in variants]
        return variants, scores


@stub.local_entrypoint()
def get_evoprotgrad_variants(sequence: str, output_csv_file: str = None, output_fasta_file: str = None, experts: str = "esm", n_steps: int = 100, parallel_chains: int = 20, max_mutations: int = -1, random_seed: int = None):
    from .evoprotgrad import EvoProtGrad
    from helix.utils import dataframe_to_fasta, count_mutations

    max_chains_per_call = 30
    experts = experts.split(",")
    evoprotgrad = EvoProtGrad(experts=experts)

    if output_csv_file is None and output_fasta_file is None:
        raise Exception(
            "Must specify either output_csv_file or output_fasta_file")

    num_calls = parallel_chains // max_chains_per_call
    remaining_chains = parallel_chains % max_chains_per_call
    print(
        f"Running {parallel_chains} parallel chains in {num_calls+1} containers")

    results = []
    for variants, scores in evoprotgrad.evolve.starmap([(sequence, n_steps, remaining_chains, max_mutations, random_seed)] + [(sequence, n_steps, max_chains_per_call, max_mutations, random_seed) for _ in range(num_calls)], return_exceptions=True):
        if isinstance(variants, Exception):
            print(f"Error: {variants}")
        else:
            for variant, score in zip(variants, scores):
                num_mutations = sum(1 for wt, mut in zip(
                    sequence, variant) if wt != mut)
                results.append({
                    'variant': variant.replace(' ', ''),
                    'score': score,
                    'num_mutations': num_mutations,
                    'experts': ' '.join(experts),
                    'n_steps': n_steps,
                    'max_mutations': max_mutations,
                    'random_seed': random_seed
                })

    print(f"Successfully generated {len(results)} variants")

    # Convert results to a DataFrame
    df_results = pd.DataFrame(results)

    mutations_report = count_mutations(
        sequence, list(df_results['variant'].values))
    pprint(mutations_report)
    # hash the sequence to get an ID
    df_results['id'] = df_results['variant'].apply(
        lambda x: hashlib.sha1(x.encode()).hexdigest())

    # Remove duplicates
    df_results.drop_duplicates(subset=['id'], inplace=True)

    # Remove variants with no mutations
    df_results = df_results[df_results['num_mutations'] > 0]

    df_results['mutations'] = df_results['variant'].apply(
        lambda x: ', '.join([f"{wt}{pos+1}{mut}" for pos, (wt, mut) in enumerate(zip(sequence, x)) if wt != mut]))

    # Sort the DataFrame by score in descending order
    df_results.sort_values(by='score', ascending=False, inplace=True)

    if output_csv_file is not None:
        df_results.to_csv(output_csv_file, index=False)
    if output_fasta_file is not None:
        with open(output_fasta_file, "w") as f:
            fasta_content = dataframe_to_fasta(
                df_results, id_col='id', seq_col='variant')
            f.write(fasta_content)
