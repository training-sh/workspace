import os
c.ServerApp.ip='0.0.0.0'
c.ServerApp.port=8888
c.ServerApp.open_browser=False
c.ServerApp.root_dir='/workspace'
c.IdentityProvider.token=os.environ['JUPYTER_TOKEN']
c.ServerApp.terminals_enabled=True
