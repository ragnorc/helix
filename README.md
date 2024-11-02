<div align="center">

### **🧬 Helix: Modular Components for Bioinformatics Workflows with Modal**

[![PyPI version](https://badge.fury.io/py/helixbio.svg)](https://badge.fury.io/py/helixbio)

</div>

---

<br></br>

Helix provides a set of modular, Lego-like components for constructing bioinformatics workflows. By abstracting away infrastructure complexities, Helix allows researchers to focus on biological problems rather than computational logistics. Built on [Modal](https://modal.com), it offers efficient cloud-based execution for large-scale computational tasks. Leveraging Modal's features, Helix provides flexible environments, seamless integrations with various services, efficient data management, advanced job scheduling, and built-in debugging tools, all while enabling easy deployment of web services.

## 🧩 Core Philosophy

Helix provides modular components for building scalable bioinformatics pipelines. We've abstracted away infrastructure complexities, allowing researchers to construct workflows using a clean Python API. By leveraging Modal's cloud capabilities, Helix offers powerful distributed computing without the typical overhead. Our design emphasizes programmatic interfaces over CLIs, enabling seamless integration into existing codebases. The goal is to empower bioinformaticians to focus on algorithm development and data analysis, rather than resource management and deployment logistics.

## ⚙️ Getting Started

1. Create an account at [modal.com](https://modal.com) for cloud execution access.
2. Install Helix: `pip install helixbio` (Python 3.10+ required)
3. Set up Modal: `modal token new`

## 🧬 Examples

Here are some examples of how to run various functions using the Modal app context:

### Compute Protein Embeddings with ESM

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

### Predict Protein Structures with Chai and ESMFold

```python
from helix.core import app
from helix.functions import chai, esmfold

# Example for Chai
with app.run():
    sequences = [
        "MALLWMRLLPLLALLALWGPD",
        "MKTVRQERLKSIVRILERSKEPVSGAQ"
    ]

    inference_params = {
        "num_recycles": 3,
        "num_samples": 1
    }
    chai_results = chai.predict_structures.remote(sequences, inference_params)
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

### Score Mutation using Protein Language Models

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
