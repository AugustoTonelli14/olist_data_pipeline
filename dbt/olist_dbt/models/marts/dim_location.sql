-- Dimension: location
-- One row per zip code prefix with coordinates

select
    geolocation_zip_code_prefix as location_key,
    geolocation_zip_code_prefix as zip_code_prefix,
    geolocation_city as city,
    geolocation_state as state,
    geolocation_lat as latitude,
    geolocation_lng as longitude
from read_parquet('../../data/processed/geolocation.parquet')
