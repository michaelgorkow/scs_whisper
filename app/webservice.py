import logging
import sys
import numpy as np
from fastapi import FastAPI, Request, Query
from whisper import tokenizer
from openai_whisper.core import transcribe, language_detection, load_audio

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

LANGUAGE_CODES=sorted(list(tokenizer.LANGUAGES.keys()))

app = FastAPI()

@app.post("/asr", tags=["Endpoints"])
async def asr(request: Request):
   # task : Union[str, None] = Query(default="transcribe", enum=["transcribe", "translate"]),
   # language: Union[str, None] = Query(default=None, enum=LANGUAGE_CODES),
   # audio_file: Union[str, None] = Query(default=None),
   # encode : bool = Query(default=True, description="Encode audio first through ffmpeg")
   request_body = await request.json()
   request_body = request_body['data']
   return_data = []
   for index, task, language, audio_file, encode in request_body:
      transcription = transcribe(load_audio(audio_file, encode), task, language)
      return_data.append([index, transcription])
   return {"data": return_data}


@app.post("/detect-language", tags=["Endpoints"])
async def detect_language(request: Request):
   # audio_file: Union[str, None] = Query(default=None),
   # encode : bool = Query(default=True, description="Encode audio first through ffmpeg")
   request_body = await request.json()
   request_body = request_body['data']
   return_data = []
   for index, audio_file, encode in request_body:
      detected_lang_code = language_detection(load_audio(audio_file, encode))
      return_data.append([index, { "detected_language": tokenizer.LANGUAGES[detected_lang_code], "language_code" : detected_lang_code }])
   return {"data": return_data}