git lfs install
git lfs track "*.csv" "*.parquet" "models/**.pkl"
echo ".dvc/*"           >> .gitignore
echo "mlruns/"          >> .gitignore
