cd /d "%~dp0"
call conda activate learning-english
git pull
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
echo The Update is Finished!
pause