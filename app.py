from flask import Flask
from controllers import routes

app = Flask(__name__, template_folder='views')

routes.init_app(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)
    
    #Define paste que receberá arquivos de upload
    app.config['UPLOAD_FOLDER'] = 'static/uploads/'
    #Define o tamanho máximo de um arquivo de upload
    app.config['MAX_CONTENT_LENGHT'] = 16 * 1024 * 1024
