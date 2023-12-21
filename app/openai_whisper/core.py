import logging
import sys, os
import os
from typing import Union
from threading import Lock
import torch
import whisper
import requests
import numpy as np
from subprocess import run

# Logging
def get_logger(logger_name):
   logger = logging.getLogger(logger_name)
   logger.setLevel(logging.DEBUG)
   handler = logging.StreamHandler(sys.stdout)
   handler.setLevel(logging.DEBUG)
   handler.setFormatter(
      logging.Formatter(
      '%(name)s [%(asctime)s] [%(levelname)s] %(message)s'))
   logger.addHandler(handler)
   return logger
logger = get_logger('snowpark-container-service')

model_name= os.getenv("ASR_MODEL", "base")
if torch.cuda.is_available():
    logger.debug(f"Running on GPU")
    model = whisper.load_model(model_name, download_root='/whisper_models').cuda()
else:
    logger.debug(f"Running on CPU")
    model = whisper.load_model(model_name, download_root='/whisper_models')
model_lock = Lock()

def load_audio(file: str, encode=True, sr: int = 16000):
    """
    Open an audio file object and read as mono waveform, resampling as necessary.
    Parameters
    ----------
    file: str
        PRESIGNED_URL as described here https://docs.snowflake.com/en/sql-reference/functions/get_presigned_url
    encode: Boolean
        If true, encode audio stream to WAV before sending to whisper
    sr: int
        The sample rate to resample the audio if necessary
    Returns
    -------
    A NumPy array containing the audio waveform, in float32 dtype.
    """
    # Creating Snowpark Session
    audio_bytes = requests.get(file).content
    if encode:
        try:
            # ffmpeg to read audio data from requests
            cmd = [
                "ffmpeg",
                "-nostdin",
                "-threads", "0",
                "-i", 'pipe:',
                "-f", "s16le",
                "-ac", "1",
                "-acodec", "pcm_s16le",
                "-ar", str(16000),
                "-"
            ]
            out = run(cmd, capture_output=True, input=audio_bytes, check=True).stdout
        except Exception as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e

    return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

def transcribe(
    audio,
    task: Union[str, None],
    language: Union[str, None],
):
    options_dict = {"task" : task}
    if language:
        options_dict["language"] = language
    with model_lock:
        result = model.transcribe(audio, **options_dict)
    return result

def language_detection(audio):
    # load audio and pad/trim it to fit 30 seconds
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    with model_lock:
        _, probs = model.detect_language(mel)
    detected_lang_code = max(probs, key=probs.get)

    return detected_lang_code
