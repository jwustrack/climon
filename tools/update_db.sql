DROP TABLE climon_stats;

ALTER TABLE climon RENAME TO climon_old;

CREATE TABLE climon (time timestamp, sensor,
        metric, value,
        CONSTRAINT pk PRIMARY KEY (time, sensor, metric)) WITHOUT ROWID;

INSERT INTO climon (time, sensor, metric, value)
    SELECT time, sensor, 0, temperature FROM climon_old;

INSERT INTO climon (time, sensor, metric, value)
    SELECT time, sensor, 1, humidity FROM climon_old;
