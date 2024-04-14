# OpenAI's Whisper in Snowpark Container Services
This repository explains how to run OpenAI's [Whisper](https://github.com/openai/whisper) in Snowpark Container Services.  
Afterwards you can easily transcribe any audio file into text and detect its language.

## Requirements
* Account with Snowpark Container Services
* Docker installed

## Setup Instructions
### 1. Create image repository, stages and compute pool 
```sql
-- create image repository
CREATE OR REPLACE IMAGE REPOSITORY TEST_IMAGE_REPOSITORY;

-- Create Stages
CREATE STAGE IF NOT EXISTS WHISPER_MODELS ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') DIRECTORY = (ENABLE = TRUE);
CREATE STAGE IF NOT EXISTS AUDIO_FILES ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE') DIRECTORY = (ENABLE = TRUE);

-- Create Compute Pool
CREATE COMPUTE POOL MY_GPU_POOL
  MIN_NODES = 1
  MAX_NODES = 1
  INSTANCE_FAMILY = GPU_NV_S;
```

### 2. Clone this repository
```bash
git clone https://github.com/michaelgorkow/scs_whisper.git
```

### 3. Build & Upload the container
```cmd
cd scs_whisper
docker build --platform linux/amd64 -t <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/<DATABASE>/<SCHEMA>/TEST_IMAGE_REPOSITORY/whisper_app:latest .
docker push <ORGNAME>-<ACCTNAME>.registry.snowflakecomputing.com/<DATABASE>/<SCHEMA>/TEST_IMAGE_REPOSITORY/whisper_app:latest
```

### 4. Upload files to stages  
Use your favourite way of uploading files and upload 
* the `spec.yml` to stage `WHISPER_APP`
* the audio files to stage `AUDIO_FILES`

### 5. Create the Whisper Service
```sql
-- Create Service
CREATE SERVICE WHISPER_APP
  IN COMPUTE POOL MY_GPU_POOL
  FROM @WHISPER_APP
  SPEC='spec.yml'
  MIN_INSTANCES=1
  MAX_INSTANCES=1;

-- Verify Service is running
SELECT SYSTEM$GET_SERVICE_STATUS('WHISPER_APP');
```

### 6. Create the service functions for language detection and transcription
```sql
-- Function to detect language from audio file
CREATE OR REPLACE FUNCTION DETECT_LANGUAGE(AUDIO_FILE TEXT, ENCODE BOOLEAN)
RETURNS VARIANT
SERVICE=WHISPER_APP
ENDPOINT=API
AS '/detect-language';

-- Function to transcribe audio files
CREATE OR REPLACE FUNCTION TRANSCRIBE(TASK TEXT, LANGUAGE TEXT, AUDIO_FILE TEXT, ENCODE BOOLEAN)
RETURNS VARIANT
SERVICE=WHISPER_APP
ENDPOINT=API
AS '/asr';
```

### 7. Call the service functions using files from a Directory Table
```sql
-- Run Whisper on a files in a stage
SELECT RELATIVE_PATH, 
       GET_PRESIGNED_URL('@<DATABASE>.<SCHEMA>.AUDIO_FILES', RELATIVE_PATH) AS PRESIGNED_URL,
       DETECT_LANGUAGE(PRESIGNED_URL,True)  AS WHISPER_RESULTS,
       WHISPER_RESULTS['detected_language']::text as DETECTED_LANGUAGE
FROM DIRECTORY('@<DATABASE>.<SCHEMA>.AUDIO_FILES');

SELECT RELATIVE_PATH, 
       GET_PRESIGNED_URL('@<DATABASE>.<SCHEMA>.AUDIO_FILES', RELATIVE_PATH) AS PRESIGNED_URL,
       TRANSCRIBE('transcribe','',PRESIGNED_URL,True) AS WHISPER_RESULTS,
       WHISPER_RESULTS['text']::TEXT as EXTRACTED_TEXT
FROM DIRECTORY('@<DATABASE>.<SCHEMA>.AUDIO_FILES');
```

### 8. Clean your environment
```sql
-- Clean Up
DROP SERVICE WHISPER_APP;
DROP COMPUTE POOL MY_GPU_POOL;
```

### Debugging: View Logs
If you want to know what's happening inside the container, you can retrieve the logs at any time.
```sql
-- See logs of container
SELECT value AS log_line
FROM TABLE(
 SPLIT_TO_TABLE(SYSTEM$GET_SERVICE_LOGS('whisper_app', 0, 'proxy'), '\n')
  );
```

## Demo Video
https://github.com/michaelgorkow/scs_whisper/assets/28981844/9834dc43-932e-4d53-ade2-467f25f5da6d



