# When to use a GPU (and Colab)

Everything runs locally by default. Only three steps benefit from a GPU:

| Step | Local (Apple Silicon) | Free GPU (Colab / Kaggle) |
| --- | --- | --- |
| Sentence embeddings (JobBERT, mpnet, bge) | Fine: tens of thousands of short texts in minutes on the Mac GPU (`device="mps"`) | Only for very large sets (Web Data Commons) |
| BERTopic | Fine once embeddings are cached | Not needed |
| DistilBERT fine-tuning (classifier comparison) | Possible but slow | **Use a GPU** |

## Running the repo in Colab

1. *Runtime → Change runtime type → T4 GPU*.
2. Open the notebook from GitHub: *File → Open notebook → GitHub → `ella-garcia/ai-job-titles`*.
3. The first cell clones the repo, installs `requirements.txt`, mounts Drive and points `AJT_DATA` at `MyDrive/ai-job-titles-data`.
4. Secrets go in the Colab secrets panel (key icon): `GITHUB_TOKEN` (the repo is private: a fine-grained token with read access to `ella-garcia/ai-job-titles`), `GCP_PROJECT`, `KAGGLE_USERNAME`, `KAGGLE_KEY`. `pipeline.config.secret()` reads them there automatically.

Colab differences to keep in mind:

- **Sessions are wiped** on disconnect, after ~90 idle minutes, and at ~12 hours. Write everything to Drive; every step in `pipeline/` is safe to re-run.
- **Python can't be pinned.** Each run saves `pip-freeze.txt` and the git commit in `runs/<date>/`.
- **Save metrics, not checkpoints.** Keep DistilBERT results (F1, confusion matrices) in `runs/`; don't store model weights on Drive.
- **Commit code from your laptop**, not from Colab. Use Colab to run, not to edit.

The `requirements.txt` used by Colab is generated from the lock file: `uv export --no-hashes --no-dev -o requirements.txt` (run it after changing dependencies).

For a free alternative, Kaggle Notebooks give ~30 GPU hours a week and run the same notebook.
