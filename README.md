# mtgo-analytics
### Usage
1.
```
git clone git@github.com:Badaro/MTGODecklistCache.git
cd MTGODecklistCache && git pull && cd ..
python -m pip install -r requirements.txt
```

2.
```
python analyze.py get-filelist --after_date="2024-08-26" --format="pioneer"
```

3.
```
python analyze.py copy-working-files
```

4.
```
python analyze.py enrich
```
