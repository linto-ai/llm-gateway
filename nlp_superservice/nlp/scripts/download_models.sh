mkdir -p assets
cd assets

mkdir -p sentence-transformers
cd sentence-transformers

git lfs install
git clone https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
git clone https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2