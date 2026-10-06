       IDENTIFICATION DIVISION.
       PROGRAM-ID. WEATHER-READER.

       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT EBCDIC-FILE ASSIGN TO
               'ebcdic_data/weather_input.ebcdic'
               ORGANIZATION IS LINE SEQUENTIAL.

           SELECT OUTPUT-FILE ASSIGN TO
               'output_cobol/weather_map.txt'
               ORGANIZATION IS LINE SEQUENTIAL.

       DATA DIVISION.
       FILE SECTION.
       FD  EBCDIC-FILE.
       01  EBCDIC-RECORD PIC X(100).

       FD  OUTPUT-FILE.
       01  OUTPUT-RECORD PIC X(100).

       WORKING-STORAGE SECTION.
       01  WS-EOF-FLAG PIC X VALUE 'N'.
       01  WS-LINE-COUNT PIC 999 VALUE 0.
       01  WS-CHAR-INDEX PIC 999.
       01  WS-CURRENT-CHAR PIC X.
       01  WS-CURRENT-BYTE PIC 999.
       01  WS-FILTERED-LINE PIC X(50).
       01  WS-OUTPUT-LINE PIC X(50).
       01  WS-HEADER-PROCESSED PIC X VALUE 'N'.

      *    EBCDIC-to-ASCII weather character mappings
       01  WS-EBCDIC-CHARS.
           05  FILLER PIC X(1) VALUE X'E3'.  *> EBCDIC T = 0xE3
           05  FILLER PIC X(1) VALUE X'D9'.  *> EBCDIC R = 0xD9
           05  FILLER PIC X(1) VALUE X'C6'.  *> EBCDIC F = 0xC6
           05  FILLER PIC X(1) VALUE X'C8'.  *> EBCDIC H = 0xC8
           05  FILLER PIC X(1) VALUE X'D3'.  *> EBCDIC L = 0xD3
           05  FILLER PIC X(1) VALUE X'C3'.  *> EBCDIC C = 0xC3
           05  FILLER PIC X(1) VALUE X'E2'.  *> EBCDIC S = 0xE2
           05  FILLER PIC X(1) VALUE X'4B'.  *> EBCDIC . = 0x4B
       01  WS-ASCII-CHARS VALUE 'TRFHLCS.'.
       01  WS-WEATHER-TABLE REDEFINES WS-ASCII-CHARS.
           05  WS-WEATHER-CHAR PIC X OCCURS 8 TIMES.

       01  SEPARATOR-LINE
           PIC X(50) VALUE
           '=================================================='.
       01  TITLE-LINE
           PIC X(50) VALUE
           '  WEATHER MAP FORECAST  (COBOL Reader)'.
       01  DASH-LINE
           PIC X(50) VALUE
           '--------------------------------------------------'.
       01  LEGEND-HEADER
           PIC X(50) VALUE
           '  Legend:'.

       PROCEDURE DIVISION.
           OPEN INPUT EBCDIC-FILE.
           OPEN OUTPUT OUTPUT-FILE.

      *    Write header
           MOVE SEPARATOR-LINE TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE TITLE-LINE TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE SEPARATOR-LINE TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

      *    Process file
           PERFORM UNTIL WS-EOF-FLAG = 'Y'
               READ EBCDIC-FILE
                   AT END
                       MOVE 'Y' TO WS-EOF-FLAG
                   NOT AT END
                       PERFORM PROCESS-LINE
               END-READ
           END-PERFORM.

      *    Write separator and legend
           MOVE DASH-LINE TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE LEGEND-HEADER TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    T = Temp High' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    R = Rain' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    F = Cold Front' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    H = High Pressure' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    L = Low Pressure' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    C = Cloudy' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    S = Snow' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE '    . = Clear' TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           MOVE SEPARATOR-LINE TO OUTPUT-RECORD.
           WRITE OUTPUT-RECORD.

           CLOSE EBCDIC-FILE.
           CLOSE OUTPUT-FILE.
           STOP RUN.

       PROCESS-LINE.
           ADD 1 TO WS-LINE-COUNT.

      *    First line is header info
           IF WS-LINE-COUNT = 1
               MOVE EBCDIC-RECORD TO OUTPUT-RECORD
               STRING '  ' DELIMITED BY SIZE
                      EBCDIC-RECORD DELIMITED BY '  '
                   INTO OUTPUT-RECORD
               END-STRING
               WRITE OUTPUT-RECORD
               MOVE DASH-LINE TO OUTPUT-RECORD
               WRITE OUTPUT-RECORD
               MOVE 'Y' TO WS-HEADER-PROCESSED
           ELSE
      *        Process weather lines - filter valid characters
               PERFORM FILTER-WEATHER-LINE
               MOVE WS-FILTERED-LINE TO OUTPUT-RECORD
               STRING '  ' DELIMITED BY SIZE
                      WS-FILTERED-LINE DELIMITED BY SPACES
                   INTO OUTPUT-RECORD
               END-STRING
               WRITE OUTPUT-RECORD
           END-IF.

       FILTER-WEATHER-LINE.
           MOVE SPACES TO WS-FILTERED-LINE.
           MOVE 1 TO WS-CHAR-INDEX.

           PERFORM VARYING WS-CHAR-INDEX
               FROM 1 BY 1
               UNTIL WS-CHAR-INDEX > LENGTH OF EBCDIC-RECORD
               MOVE FUNCTION ORD(EBCDIC-RECORD(WS-CHAR-INDEX:1))
                   TO WS-CURRENT-BYTE

      *        Check if byte matches any EBCDIC weather character
               EVALUATE WS-CURRENT-BYTE
                   WHEN 227  *> EBCDIC T (0xE3 = 227)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'T' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 217  *> EBCDIC R (0xD9 = 217)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'R' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 198  *> EBCDIC F (0xC6 = 198)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'F' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 200  *> EBCDIC H (0xC8 = 200)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'H' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 211  *> EBCDIC L (0xD3 = 211)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'L' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 195  *> EBCDIC C (0xC3 = 195)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'C' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 226  *> EBCDIC S (0xE2 = 226)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              'S' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN 75   *> EBCDIC . (0x4B = 75)
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              '.' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
                   WHEN OTHER
                       STRING WS-FILTERED-LINE DELIMITED BY SPACES
                              ' ' DELIMITED BY SIZE
                           INTO WS-FILTERED-LINE
                       END-STRING
               END-EVALUATE
           END-PERFORM.
