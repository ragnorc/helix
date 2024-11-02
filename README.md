<div align="center">
logo
<hr>

### **🧬 Helix: Modular Components for Bioinformatics Workflows with Modal**

[![PyPI version](https://badge.fury.io/py/helixbio.svg)](https://badge.fury.io/py/helixbio)

</div>

---

Helix provides a set of modular, Lego-like components for constructing bioinformatics workflows. By abstracting away infrastructure complexities, Helix allows researchers to focus on biological problems rather than computational logistics. Built on [Modal](https://modal.com), it offers efficient cloud-based execution for large-scale computational tasks.

## 🧩 Core Philosophy

Helix is designed to offer flexible, scalable "building blocks" for bioinformatics pipelines. These components abstract environments and infrastructure, allowing for the rapid assembly of complex workflows. The focus is on leveraging Modal's features to provide a powerful, yet user-friendly platform for biological computation.

## 🛠 Key Features

1. **Flexible Environments**:

   - Bring your own Docker image or build one in Python
   - Scale resources dynamically as needed
   - Access state-of-the-art GPUs (H100s, A100s) for high-performance computing

2. **Seamless Integrations**:

   - Export function logs to Datadog or any OpenTelemetry-compatible provider
   - Mount cloud storage from major providers (S3, R2, etc.)

3. **Efficient Data Management**:

   - Utilize various storage solutions: network volumes, key-value stores, queues
   - Provision and interact with storage using familiar Python syntax

4. **Advanced Job Scheduling**:

   - Set up cron jobs, retries, and timeouts
   - Optimize resource usage through batching capabilities

5. **Web Service Deployment**:

   - Create custom domains for your services
   - Set up streaming and websockets
   - Serve functions as secure HTTPS endpoints

6. **Built-In Debugging Tools**:
   - Use the Modal shell for interactive debugging
   - Set breakpoints to quickly identify and resolve issues

## ⚙️ Getting Started

1. Create an account at [modal.com](https://modal.com) for cloud execution access.
2. Install Helix: `pip install helixbio` (Python 3.10+ required)
3. Set up Modal: `modal token new`

Helix aims to empower bioinformaticians and computational biologists by providing a robust set of cloud-enabled tools and abstractions, streamlining the development of scalable and efficient bioinformatics pipelines.

## 🧬 Examples

Here are some examples of how to run various functions using the Modal app context:

### Protein Embeddings

    ```python
    from helix.core import app
    from helix.functions.embedding import get_protein_embeddings
    with app.run():
        sequences = [
            "MALLWMRLLPLLALLALWGPD",
            "MKTVRQERLKSIVRILERSKEPVSGAQ"
        ]
        result = get_protein_embeddings.remote(
            sequences,
            model_name="facebook/esm2_t33_650M_UR50D",
            embedding_strategy="cls"
        )
    ```

### Protein Structures

    ```python
    from helix.core import app
    from helix.functions import chai, esmfold

    # Example for Chai
    with app.run():
        sequences = [
            "MALLWMRLLPLLALLALWGPD",
            "MKTVRQERLKSIVRILERSKEPVSGAQ"
        ]
        sequence_ids = ["seq1", "seq2"]
        inference_params = {
            "num_recycles": 3,
            "num_samples": 1
        }
        chai_results = chai.predict_structures.remote(sequences, sequence_ids, inference_params)
        print(f"Chai predicted {len(chai_results)} structures")

    # Example for ESMFold
    with app.run():
        sequences = [
            "MALLWMRLLPLLALLALWGPD",
            "MKTVRQERLKSIVRILERSKEPVSGAQ"
        ]
        esmfold_results = esmfold.predict_structures.remote(sequences, batch_size=2)
        print(f"ESMFold predicted {len(esmfold_results)} structures")
    ```

### Mutation Scoring

Mutation scoring uses pre-trained language models to evaluate the impact of amino acid substitutions in protein sequences. This implementation is based on the methods developed by Brian Hie and colleagues, as described in their Nature Biotechnology paper (Hie et al., 2024). The function supports different scoring methods:

1. "wildtype_marginal": Computes the difference in log probability between the mutant and wild-type amino acids without masking.
2. "masked_marginal": Masks each position before scoring.
3. "pppl": (Pseudo-perplexity) Calculates the change in model perplexity caused by the mutation.

These methods have been shown to be effective in guiding the evolution of human antibodies and other proteins.

Here's an example of how to use the mutation scoring function:

    ```python
    from helix.core import app
    from helix.functions.scoring.protein import score_mutations

    with app.run():
        # Define the sequence and mutations
        sequence = "MALLWMRLLPLLALLALWGPD"
        mutations = ["M1A", "L2A", "W5A"]

        # Define model and metric
        model_name = "facebook/esm2_t33_650M_UR50D"
        metric = "wildtype_marginal"

        # Score mutations
        scores = score_mutations.remote(
            model_name=model_name,
            sequence=sequence,
            mutations=mutations,
            metric=metric
        )
        print(f"Scores for {model_name} using {metric}:")
        print(scores)

    ```

Reference:
Hie, B.L., Shanker, V.R., Xu, D. et al. Efficient evolution of human antibodies from general protein language models. Nat Biotechnol 42, 275–283 (2024). https://doi.org/10.1038/s41587-023-01763-2

    ```
