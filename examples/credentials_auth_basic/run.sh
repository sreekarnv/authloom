pip uninstall ../../dist/authloom-0.1.0.dev0-py3-none-any.whl -y
pip install ../../dist/authloom-0.1.0.dev0-py3-none-any.whl
pip install -r requirements.txt
alembic upgrade head
fastapi dev
