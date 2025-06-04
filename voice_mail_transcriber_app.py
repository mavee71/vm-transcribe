from flask import Flask, request, render_template_string
import os
import tempfile
import soundfile as sf
import speech_recognition as sr

app = Flask(__name__)

UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

HTML_FORM = '''
<!doctype HTML>
<style>
  /* This CSS rule targets all h1 elements */
  h1 {
    margin-bottom: 20px; /* Adjust 20px to whatever space you want */
    font-family: Arial, sans-serif; /* Example: common font */
  }

  /* Class for instructional text */
  .instructions {
    font-size: 0.95em; /* Slightly smaller or adjust as needed */
    margin-top: 5px;
    margin-bottom: 10px;
    color: #333; /* Dark gray */
    font-family: Arial, sans-serif; /* Example: common font */
  }

  /* Styling for the results/error headings */
  .results-heading {
    margin-top: 15px;
    margin-bottom: 5px;
    font-size: 1.2em; /* Example size for these subheadings */
    font-family: Arial, sans-serif;
  }
  
  /* Styling for the preformatted text block */
  pre {
    white-space: pre-wrap;   /* CSS3 */
    word-wrap: break-word; /* Internet Explorer 5.5+ */
    background-color: #f9f9f9; /* Light background for the transcript */
    border: 1px solid #ddd;
    padding: 10px;
    font-family: monospace;
  }

  /* Basic styling for the form */
  form {
    margin-top: 15px;
    margin-bottom: 20px;
  }

  input[type="file"] {
    margin-right: 10px;
    margin-bottom: 10px; /* Space below file input if window is narrow */
  }

  input[type="submit"] {
    padding: 8px 15px;
    background-color: #0078d4; /* Example SharePoint-like blue */
    color: white;
    border: none;
    cursor: pointer;
    border-radius: 3px;
  }
  input[type="submit"]:hover {
    background-color: #005a9e;
  }
</style>
<title>Voicemail Transcriber</title>
<h1>OpX - Voicemail Transcriber (Beta)</h1>
<h2>Upload a voicemail file (type .wav) >> Click the "Transcribe" button<h2>
<h2>Allow 10-20 seconds for transcription to complete<h2>
<form method=post enctype=multipart/form-data>
  <input type=file name=voicemail accept="audio/wav">
  <input type=submit value=Transcribe>
</form>
{% if transcription %}
  <h2>Transcription:</h2>
  <pre style="white-space: pre-wrap; word-wrap: break-word;">
    {{ transcription }}
  </pre>
{% elif error %}
  <h2 style="color:red;">Error:</h2>
  <pre style="white-space: pre-wrap; word-wrap: break-word;">
    {{ error }}
  </pre>
{% endif %}

'''

def transcribe_wav_with_conversion(wav_filepath):
    try:
        data, samplerate = sf.read(wav_filepath)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
            temp_wav_path = temp_wav.name
            sf.write(temp_wav_path, data, samplerate, subtype='PCM_16')
        recognizer = sr.Recognizer()
        with sr.AudioFile(temp_wav_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)
            return text, None
    except sf.LibsndfileError as e:
        return None, f"Could not read or convert the audio file: {e}"
    except sr.UnknownValueError:
        return None, "Google Speech Recognition could not understand audio."
    except sr.RequestError as e:
        return None, f"Could not request results from Google Speech Recognition; {e}"
    except Exception as e:
        return None, f"Error during processing: {e}"
    finally:
        try:
            os.remove(temp_wav_path)
        except Exception:
            pass

@app.route('/', methods=['GET', 'POST'])
def upload_and_transcribe():
    transcription = error = None
    if request.method == 'POST':
        if 'voicemail' not in request.files:
            error = 'No file part'
        else:
            file = request.files['voicemail']
            if file.filename == '':
                error = 'No selected file'
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav', dir=UPLOAD_FOLDER) as temp_file:
                    file.save(temp_file.name)
                    transcription, error = transcribe_wav_with_conversion(temp_file.name)
                os.remove(temp_file.name)
    return render_template_string(HTML_FORM, transcription=transcription, error=error)

# Allow this app to be displayed in an iframe (no X-Frame-Options header)
@app.after_request
def allow_iframe(response):
    # Remove any existing X-Frame-Options header
    response.headers.pop("X-Frame-Options", None)
    # (Optional) You could also set Content-Security-Policy if needed:
    # response.headers["Content-Security-Policy"] = "frame-ancestors https://yourtenant.sharepoint.com"
    return response


if __name__ == '__main__':
    app.run(debug=True)


