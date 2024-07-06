@echo off
call mackbot\extract_gameparams.bat

echo Extracting GameParams and translator file
cd WoWS-GameParams
python OneFileToRuleThemAll.py
move GameParams-0.json ../data/
robocopy language ..\mackbot\language /e /NFL /NDL /NJH /NJS /nc /ns /np
cd ..

cd mackbot
python extractingGlobalMO.py
rmdir /S /Q language

echo Splitting and translating...
python GameParamsSplitter.py
cd ..

echo Uploading data to live and dev DB...
python upload_to_db.py --update_all

echo Uploading Done