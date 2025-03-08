import os
import sys
import zipfile
from flask import Flask, render_template, request, jsonify
import yt_dlp
import shutil

app = Flask(__name__)
DOWNLOAD_FOLDER = os.path.join(os.getcwd(), "downloads")  # Diretório de downloads
BIN_FOLDER = os.path.join(os.getcwd(), "bin")  # Pasta bin com o ffmpeg

# Criar a pasta de downloads se não existir
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

# Função melhorada para extrair a pasta bin do .exe ou arquivo zip
def extract_bin():
    if not os.path.exists(BIN_FOLDER):
        print("Extraindo a pasta 'bin'...")
        os.makedirs(BIN_FOLDER, exist_ok=True)
        
        # Determinar o caminho do arquivo zip dependendo do contexto
        if getattr(sys, 'frozen', False):
            # Quando estiver rodando como .exe (PyInstaller)
            bin_zip_path = os.path.join(sys._MEIPASS, 'bin.zip')
        else:
            # Durante o desenvolvimento
            bin_zip_path = os.path.join(os.getcwd(), 'bin.zip')
        
        try:
            # Tentar extrair o arquivo bin.zip
            if os.path.exists(bin_zip_path):
                with zipfile.ZipFile(bin_zip_path, 'r') as zip_ref:
                    zip_ref.extractall(os.getcwd())  # Extrair para o diretório atual
                print("Pasta 'bin' extraída com sucesso.")
            else:
                print(f"Arquivo bin.zip não encontrado em: {bin_zip_path}")
                # Procurar o bin.zip na pasta atual como fallback
                local_bin_zip = os.path.join(os.getcwd(), 'bin.zip')
                if os.path.exists(local_bin_zip):
                    with zipfile.ZipFile(local_bin_zip, 'r') as zip_ref:
                        zip_ref.extractall(os.getcwd())
                    print("Pasta 'bin' extraída do arquivo local com sucesso.")
        except Exception as e:
            print(f"Erro ao extrair bin.zip: {str(e)}")

# Função para garantir que o ffmpeg esteja disponível
def check_ffmpeg():
    ffmpeg_path = os.path.join(BIN_FOLDER, 'ffmpeg.exe')
    print(f"Procurando FFmpeg em: {ffmpeg_path}")
    
    if not os.path.exists(ffmpeg_path):
        # Tentar encontrar ffmpeg em locais alternativos
        if getattr(sys, 'frozen', False):
            # Verificar se ffmpeg.exe está diretamente em _MEIPASS (dentro do executável)
            bundled_ffmpeg = os.path.join(sys._MEIPASS, 'ffmpeg.exe')
            if os.path.exists(bundled_ffmpeg):
                # Copiar para a pasta bin
                shutil.copy2(bundled_ffmpeg, ffmpeg_path)
                print(f"FFmpeg copiado de {bundled_ffmpeg} para {ffmpeg_path}")
            else:
                print(f"FFmpeg não encontrado em: {bundled_ffmpeg}")
                raise FileNotFoundError(f"FFmpeg não encontrado em: {ffmpeg_path}")
        else:
            raise FileNotFoundError(f"FFmpeg não encontrado em: {ffmpeg_path}")
    
    # Configurar variáveis de ambiente para o ffmpeg
    os.environ['FFMPEG_BINARY'] = ffmpeg_path
    os.environ['PATH'] = BIN_FOLDER + os.pathsep + os.environ['PATH']
    print(f"FFmpeg configurado com sucesso: {ffmpeg_path}")

# Extrair a pasta bin e verificar ffmpeg
try:
    extract_bin()
    check_ffmpeg()
except Exception as e:
    print(f"AVISO: Problema ao configurar FFmpeg: {str(e)}")
    print("O aplicativo tentará continuar, mas pode falhar ao processar áudio/vídeo.")

def progress_hook(d):
    if d['status'] == 'downloading':
        print(f"Baixando: {d['_percent_str']} - Velocidade: {d['_speed_str']}")
    elif d['status'] == 'finished':
        print(f"Download concluído: {d['filename']}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    data = request.json
    url = data.get("url")
    format = data.get("format", "mp4")

    if not url:
        return jsonify({"error": "URL inválida"}), 400

    # Validar a URL (simples verificação para YouTube, Shorts e Reels)
    if not (url.startswith('https://www.youtube.com') or 
            url.startswith('https://youtu.be') or
            url.startswith('https://www.instagram.com/reel')):
        return jsonify({"error": "URL deve ser do YouTube (incluindo Shorts) ou Instagram Reels"}), 400

    # Caminho de download personalizado
    download_path = r"E:\Pasta LUL\baixados"  # Caminho desejado

    # Verificar se a pasta existe, caso contrário usar o Desktop
    if not os.path.exists(download_path):
        print(f"Pasta '{download_path}' não encontrada. Usando Desktop como fallback.")
        download_path = os.path.join(os.path.expanduser("~"), "Desktop")  # Pasta Desktop

    # Configuração do yt-dlp com base no formato
    ydl_opts = {
        'format': 'bestaudio/best' if format == 'mp3' else 'bestvideo+bestaudio',
        'outtmpl': os.path.join(download_path, "%(title)s.%(ext)s"),
        'progress_hooks': [progress_hook],
        'quiet': False  # Mostrar o progresso no terminal
    }
    
    # Adicionar postprocessors apenas para mp3
    if format == 'mp3':
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3'}]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extração das informações do vídeo
            info = ydl.extract_info(url, download=True)
            # Obter o nome final do arquivo
            filename = ydl.prepare_filename(info)
            
            # Se o formato for mp3, ajustar o nome do arquivo
            if format == 'mp3':
                filename = filename.rsplit('.', 1)[0] + '.mp3'
            
            return jsonify({"message": "Download concluído!", 
                           "file": filename, 
                           "url": url, 
                           "format": format})
    
    except yt_dlp.DownloadError as e:
        return jsonify({"error": f"Erro ao baixar o vídeo: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"Erro inesperado: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8000)