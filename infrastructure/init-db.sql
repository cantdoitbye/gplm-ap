-- Initialize PostGIS extension and create necessary functions

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Verify PostGIS installation
SELECT PostGIS_Full_Version();

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create function to compute geometry centroid
CREATE OR REPLACE FUNCTION compute_centroid()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.geometry IS NOT NULL THEN
        NEW.centroid := ST_Centroid(NEW.geometry);
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create spatial reference system check
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM spatial_ref_sys WHERE srid = 4326) THEN
        INSERT INTO spatial_ref_sys (srid, auth_name, auth_srid, srtext, proj4text)
        VALUES (
            4326,
            'EPSG',
            4326,
            'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AUTHORITY["EPSG","4326"]]',
            '+proj=longlat +datum=WGS84 +no_defs'
        );
    END IF;
END
$$;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aikosh5;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aikosh5;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO aikosh5;

-- Note: The property_centroid trigger will be created by SQLAlchemy after tables are created
-- or you can run this after tables are created:
-- CREATE TRIGGER update_property_centroid
--     BEFORE INSERT OR UPDATE ON properties
--     FOR EACH ROW
--     EXECUTE FUNCTION compute_centroid();
