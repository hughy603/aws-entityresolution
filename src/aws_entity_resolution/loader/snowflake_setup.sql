-- File stage for loading Entity Resolution results
CREATE OR REPLACE FILE FORMAT entity_resolution_json_format
    TYPE = 'JSON'
    STRIP_OUTER_ARRAY = TRUE
    ALLOW_DUPLICATE = FALSE;

-- External stage using the storage integration
CREATE OR REPLACE STAGE entity_resolution_stage
    URL = 's3://:bucket/:prefix'
    STORAGE_INTEGRATION = :storage_integration_name
    FILE_FORMAT = entity_resolution_json_format;

-- Target table for matched records
CREATE TABLE IF NOT EXISTS :target_table (
    ID VARCHAR NOT NULL,
    NAME VARCHAR,
    EMAIL VARCHAR,
    MATCH_ID VARCHAR,
    MATCH_SCORE FLOAT,
    LAST_UPDATED TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (ID)
);

-- Stream to track changes
CREATE OR REPLACE STREAM :target_table_stream ON TABLE :target_table;
