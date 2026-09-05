       IDENTIFICATION DIVISION.
       PROGRAM-ID. BOI-BANKING-ENGINE.
       AUTHOR. Codex.

       ENVIRONMENT DIVISION.
       CONFIGURATION SECTION.
       SOURCE-COMPUTER. GNUCOBOL.
       OBJECT-COMPUTER. GNUCOBOL.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-CONFIG.
           05 WS-DB-PATH             PIC X(256)
              VALUE "database/banking_sim.db".
           05 WS-STOP-FILE           PIC X(256)
              VALUE "database/simulation.stop".
           05 WS-MAX-ACCOUNTS        PIC 9(6) VALUE 10000.
           05 WS-MAX-TXNS            PIC 9(7) VALUE 100000.
           05 WS-BATCH-SIZE          PIC 9(5) VALUE 1000.
           05 WS-CONTINUOUS-MODE     PIC X VALUE "N".
           05 WS-WORKER-COUNT        PIC 9(2) VALUE 4.

       01  WS-LENGTHS.
           05 LEN-8                  PIC S9(9) COMP-5 VALUE 8.
           05 LEN-9                  PIC S9(9) COMP-5 VALUE 9.
           05 LEN-10                 PIC S9(9) COMP-5 VALUE 10.
           05 LEN-11                 PIC S9(9) COMP-5 VALUE 11.
           05 LEN-12                 PIC S9(9) COMP-5 VALUE 12.
           05 LEN-14                 PIC S9(9) COMP-5 VALUE 14.
           05 LEN-16                 PIC S9(9) COMP-5 VALUE 16.
           05 LEN-18                 PIC S9(9) COMP-5 VALUE 18.
           05 LEN-20                 PIC S9(9) COMP-5 VALUE 20.
           05 LEN-24                 PIC S9(9) COMP-5 VALUE 24.
           05 LEN-32                 PIC S9(9) COMP-5 VALUE 32.
           05 LEN-48                 PIC S9(9) COMP-5 VALUE 48.
           05 LEN-64                 PIC S9(9) COMP-5 VALUE 64.
           05 LEN-128                PIC S9(9) COMP-5 VALUE 128.
           05 LEN-256                PIC S9(9) COMP-5 VALUE 256.

       01  WS-DB.
           05 DB-RESULT              PIC S9(9) COMP-5 VALUE 0.
           05 STOP-RESULT            PIC S9(9) COMP-5 VALUE 0.

       01  WS-ACCOUNT-STATE.
           05 ACCOUNT-BALANCES OCCURS 100000 TIMES
              INDEXED BY ACCOUNT-IDX PIC S9(11)V99 COMP-3 VALUE 0.
           05 ACCOUNT-STATUS OCCURS 100000 TIMES
              PIC X VALUE "A".

       01  WS-TEMP.
           05 I                      PIC 9(7) VALUE 0.
           05 J                      PIC 9(7) VALUE 0.
           05 TXN-NO                 PIC 9(7) VALUE 0.
           05 BATCH-COUNT            PIC 9(5) VALUE 0.
           05 WORKER-ID              PIC 9(2) VALUE 0.
           05 SOURCE-NUM             PIC 9(6) VALUE 0.
           05 SENDER-NUM             PIC 9(6) VALUE 0.
           05 RECEIVER-NUM           PIC 9(6) VALUE 0.
           05 MULE-NUM               PIC 9(6) VALUE 0.
           05 DEST-NUM               PIC 9(6) VALUE 0.
           05 CHAIN-NUM              PIC 9(5) VALUE 0.
           05 LAYER-NUM              PIC S9(9) COMP-5 VALUE 0.
           05 FRAUD-FLAG             PIC S9(9) COMP-5 VALUE 0.
           05 MULE-FLAG              PIC S9(9) COMP-5 VALUE 0.
           05 RAND-VALUE             COMP-2 VALUE 0.
           05 RAND-INT               PIC 9(7) VALUE 0.
           05 AMOUNT                 COMP-2 VALUE 0.
           05 NEW-BALANCE            COMP-2 VALUE 0.
           05 AVG-AMOUNT             COMP-2 VALUE 0.
           05 MONTHLY-INCOME         COMP-2 VALUE 0.

       01  WS-STRINGS.
           05 ACCT-NUM-TEXT          PIC 9(6).
           05 TXN-NUM-TEXT           PIC 9(7).
           05 CHAIN-NUM-TEXT         PIC 9(5).
           05 ACCOUNT-ID             PIC X(16).
           05 ACCOUNT-NAME           PIC X(64).
           05 ACCOUNT-TYPE           PIC X(16) VALUE "SAVINGS".
           05 ACCOUNT-STAT           PIC X(16) VALUE "ACTIVE".
           05 PHONE                  PIC X(16).
           05 OCCUPATION             PIC X(32).
           05 TXN-ID                 PIC X(24).
           05 SENDER-ID              PIC X(16).
           05 RECEIVER-ID            PIC X(16).
           05 CHANNEL                PIC X(16).
           05 TXN-STATUS             PIC X(16) VALUE "COMPLETED".
           05 DESCRIPTION            PIC X(128).
           05 EVENT-ID               PIC X(24).
           05 FRAUD-TYPE             PIC X(48).
           05 SEVERITY               PIC X(16).
           05 PATTERN-TYPE           PIC X(32).
           05 CHAIN-ID               PIC X(32).
           05 LINKED-ID              PIC X(16).
           05 LOG-LEVEL              PIC X(16).
           05 LOG-MESSAGE            PIC X(128).
           05 CONTROL-KEY            PIC X(32).
           05 CONTROL-VALUE          PIC X(32).
           05 TIMESTAMP              PIC X(24).
           05 DATE-YYYYMMDD          PIC 9(8).
           05 TIME-HHMMSS            PIC 9(8).
           05 DATE-TEXT              PIC X(8).
           05 TIME-TEXT              PIC X(8).
           05 TS-YEAR                PIC X(4).
           05 TS-MONTH               PIC X(2).
           05 TS-DAY                 PIC X(2).
           05 TS-HOUR                PIC X(2).
           05 TS-MIN                 PIC X(2).
           05 TS-SEC                 PIC X(2).

       PROCEDURE DIVISION.
       MAIN-PROCEDURE.
           PERFORM LOAD-CONFIG
           PERFORM OPEN-DATABASE
           PERFORM LOG-START
           PERFORM CREATE-ACCOUNTS
           PERFORM CREATE-MULE-NETWORKS
           PERFORM GENERATE-TRANSACTIONS
           PERFORM SET-FINISHED
           CALL "db_close_db" USING BY REFERENCE DB-RESULT
           STOP RUN.

       LOAD-CONFIG.
           ACCEPT WS-DB-PATH FROM ENVIRONMENT "BOI_DB_PATH"
           ACCEPT WS-STOP-FILE FROM ENVIRONMENT "BOI_STOP_FILE"
           ACCEPT WS-MAX-ACCOUNTS FROM ENVIRONMENT "BOI_ACCOUNTS"
           ACCEPT WS-MAX-TXNS FROM ENVIRONMENT "BOI_TRANSACTIONS"
           ACCEPT WS-BATCH-SIZE FROM ENVIRONMENT "BOI_BATCH_SIZE"
           ACCEPT WS-CONTINUOUS-MODE FROM ENVIRONMENT "BOI_CONTINUOUS"
           ACCEPT WS-WORKER-COUNT FROM ENVIRONMENT "BOI_WORKERS"

           IF WS-MAX-ACCOUNTS < 1000
              MOVE 1000 TO WS-MAX-ACCOUNTS
           END-IF
           IF WS-MAX-ACCOUNTS > 100000
              MOVE 100000 TO WS-MAX-ACCOUNTS
           END-IF
           IF WS-MAX-TXNS < 1
              MOVE 100000 TO WS-MAX-TXNS
           END-IF
           IF WS-BATCH-SIZE < 100
              MOVE 1000 TO WS-BATCH-SIZE
           END-IF
           IF WS-WORKER-COUNT < 1
              MOVE 1 TO WS-WORKER-COUNT
           END-IF.

       OPEN-DATABASE.
           CALL "db_init" USING BY REFERENCE WS-DB-PATH LEN-256 DB-RESULT
           IF DB-RESULT NOT = 0
              DISPLAY "Database open failed"
              STOP RUN
           END-IF
           CALL "db_create_schema" USING BY REFERENCE DB-RESULT
           IF DB-RESULT NOT = 0
              DISPLAY "Schema creation failed"
              STOP RUN
           END-IF
           MOVE "status" TO CONTROL-KEY
           MOVE "running" TO CONTROL-VALUE
           CALL "db_update_sim_control" USING
                BY REFERENCE CONTROL-KEY LEN-32
                BY REFERENCE CONTROL-VALUE LEN-32
                BY REFERENCE DB-RESULT.

       LOG-START.
           PERFORM BUILD-TIMESTAMP
           MOVE "INFO" TO LOG-LEVEL
           MOVE "COBOL banking engine started" TO LOG-MESSAGE
           CALL "db_insert_log" USING
                BY REFERENCE LOG-LEVEL LEN-16
                BY REFERENCE LOG-MESSAGE LEN-128
                BY REFERENCE TIMESTAMP LEN-24
                BY REFERENCE DB-RESULT.

       CREATE-ACCOUNTS.
           CALL "db_begin_txn" USING BY REFERENCE DB-RESULT
           PERFORM VARYING I FROM 1 BY 1 UNTIL I > WS-MAX-ACCOUNTS
              PERFORM BUILD-ACCOUNT-ID
              STRING "Customer " DELIMITED BY SIZE
                     ACCT-NUM-TEXT DELIMITED BY SIZE
                     INTO ACCOUNT-NAME
              END-STRING
              STRING "98" DELIMITED BY SIZE
                     ACCT-NUM-TEXT DELIMITED BY SIZE
                     INTO PHONE
              END-STRING
              COMPUTE ACCOUNT-BALANCES(I) =
                 5000 + FUNCTION MOD(I * 7919, 250000)
              IF I = 1
                 MOVE 9999999999.99 TO ACCOUNT-BALANCES(I)
              END-IF
              COMPUTE NEW-BALANCE = ACCOUNT-BALANCES(I)
              COMPUTE AVG-AMOUNT =
                 500 + FUNCTION MOD(I * 313, 25000)
              COMPUTE MONTHLY-INCOME =
                 25000 + FUNCTION MOD(I * 997, 250000)
              PERFORM PICK-OCCUPATION
              PERFORM BUILD-TIMESTAMP
              CALL "db_insert_account" USING
                   BY REFERENCE ACCOUNT-ID LEN-16
                   BY REFERENCE ACCOUNT-NAME LEN-64
                   BY REFERENCE ACCOUNT-TYPE LEN-16
                   BY REFERENCE ACCOUNT-STAT LEN-16
                   BY REFERENCE NEW-BALANCE
                   BY REFERENCE PHONE LEN-16
                   BY REFERENCE TIMESTAMP LEN-24
                   BY REFERENCE DB-RESULT
              CALL "db_insert_profile" USING
                   BY REFERENCE ACCOUNT-ID LEN-16
                   BY REFERENCE AVG-AMOUNT
                   BY REFERENCE MONTHLY-INCOME
                   BY REFERENCE OCCUPATION LEN-32
                   BY REFERENCE DB-RESULT
              ADD 1 TO BATCH-COUNT
              IF BATCH-COUNT >= WS-BATCH-SIZE
                 CALL "db_commit_txn" USING BY REFERENCE DB-RESULT
                 CALL "db_begin_txn" USING BY REFERENCE DB-RESULT
                 MOVE 0 TO BATCH-COUNT
              END-IF
           END-PERFORM
           CALL "db_commit_txn" USING BY REFERENCE DB-RESULT
           MOVE 0 TO BATCH-COUNT.

       CREATE-MULE-NETWORKS.
           CALL "db_begin_txn" USING BY REFERENCE DB-RESULT
           PERFORM VARYING CHAIN-NUM FROM 1 BY 1 UNTIL CHAIN-NUM > 50
              PERFORM CREATE-FANOUT-MULE
              PERFORM CREATE-RELAY-MULE
              PERFORM CREATE-LAYERING-MULE
           END-PERFORM
           CALL "db_commit_txn" USING BY REFERENCE DB-RESULT.

       CREATE-FANOUT-MULE.
           COMPUTE MULE-NUM = FUNCTION MOD(CHAIN-NUM * 811, WS-MAX-ACCOUNTS)
           ADD 1 TO MULE-NUM
           MOVE MULE-NUM TO SOURCE-NUM
           PERFORM BUILD-MULE-ACCOUNT-ID
           MOVE "FAN_OUT" TO PATTERN-TYPE
           PERFORM BUILD-CHAIN-ID
           MOVE 1 TO LAYER-NUM
           MOVE SPACES TO LINKED-ID
           PERFORM BUILD-TIMESTAMP
           CALL "db_insert_mule" USING
                BY REFERENCE ACCOUNT-ID LEN-16
                BY REFERENCE PATTERN-TYPE LEN-32
                BY REFERENCE CHAIN-ID LEN-32
                BY REFERENCE LAYER-NUM
                BY REFERENCE LINKED-ID LEN-16
                BY REFERENCE TIMESTAMP LEN-24
                BY REFERENCE DB-RESULT.

       CREATE-RELAY-MULE.
           MOVE "RELAY" TO PATTERN-TYPE
           PERFORM BUILD-CHAIN-ID
           PERFORM VARYING J FROM 1 BY 1 UNTIL J > 3
              COMPUTE MULE-NUM =
                 FUNCTION MOD(CHAIN-NUM * 1201 + J * 17,
                 WS-MAX-ACCOUNTS)
              ADD 1 TO MULE-NUM
              PERFORM BUILD-MULE-ACCOUNT-ID
              MOVE J TO LAYER-NUM
              COMPUTE DEST-NUM =
                 FUNCTION MOD(CHAIN-NUM * 1201 + (J + 1) * 17,
                 WS-MAX-ACCOUNTS)
              ADD 1 TO DEST-NUM
              MOVE DEST-NUM TO SOURCE-NUM
              PERFORM BUILD-LINKED-ID
              PERFORM BUILD-TIMESTAMP
              CALL "db_insert_mule" USING
                   BY REFERENCE ACCOUNT-ID LEN-16
                   BY REFERENCE PATTERN-TYPE LEN-32
                   BY REFERENCE CHAIN-ID LEN-32
                   BY REFERENCE LAYER-NUM
                   BY REFERENCE LINKED-ID LEN-16
                   BY REFERENCE TIMESTAMP LEN-24
                   BY REFERENCE DB-RESULT
           END-PERFORM.

       CREATE-LAYERING-MULE.
           MOVE "LAYERING" TO PATTERN-TYPE
           PERFORM BUILD-CHAIN-ID
           PERFORM VARYING J FROM 1 BY 1 UNTIL J > 3
              COMPUTE MULE-NUM =
                 FUNCTION MOD(CHAIN-NUM * 1877 + J * 29,
                 WS-MAX-ACCOUNTS)
              ADD 1 TO MULE-NUM
              PERFORM BUILD-MULE-ACCOUNT-ID
              MOVE J TO LAYER-NUM
              MOVE SPACES TO LINKED-ID
              PERFORM BUILD-TIMESTAMP
              CALL "db_insert_mule" USING
                   BY REFERENCE ACCOUNT-ID LEN-16
                   BY REFERENCE PATTERN-TYPE LEN-32
                   BY REFERENCE CHAIN-ID LEN-32
                   BY REFERENCE LAYER-NUM
                   BY REFERENCE LINKED-ID LEN-16
                   BY REFERENCE TIMESTAMP LEN-24
                   BY REFERENCE DB-RESULT
           END-PERFORM.

       GENERATE-TRANSACTIONS.
           CALL "db_begin_txn" USING BY REFERENCE DB-RESULT
           PERFORM UNTIL STOP-RESULT = 1
              ADD 1 TO TXN-NO
              IF TXN-NO > WS-MAX-TXNS AND WS-CONTINUOUS-MODE NOT = "Y"
                 EXIT PERFORM
              END-IF
              COMPUTE WORKER-ID =
                 FUNCTION MOD(TXN-NO, WS-WORKER-COUNT) + 1
              PERFORM GENERATE-ONE-TRANSACTION
              ADD 1 TO BATCH-COUNT
              IF BATCH-COUNT >= WS-BATCH-SIZE
                 CALL "db_commit_txn" USING BY REFERENCE DB-RESULT
                 CALL "db_check_stop" USING
                      BY REFERENCE WS-STOP-FILE LEN-256
                      BY REFERENCE STOP-RESULT
                 CALL "db_begin_txn" USING BY REFERENCE DB-RESULT
                 MOVE 0 TO BATCH-COUNT
              END-IF
           END-PERFORM
           CALL "db_commit_txn" USING BY REFERENCE DB-RESULT.

       GENERATE-ONE-TRANSACTION.
           MOVE 0 TO FRAUD-FLAG
           MOVE 0 TO MULE-FLAG
           COMPUTE SENDER-NUM =
              FUNCTION MOD(TXN-NO * 3571 + WORKER-ID * 101,
              WS-MAX-ACCOUNTS) + 1
           COMPUTE RECEIVER-NUM =
              FUNCTION MOD(TXN-NO * 8161 + WORKER-ID * 211,
              WS-MAX-ACCOUNTS) + 1
           IF RECEIVER-NUM = SENDER-NUM
              ADD 1 TO RECEIVER-NUM
              IF RECEIVER-NUM > WS-MAX-ACCOUNTS
                 MOVE 1 TO RECEIVER-NUM
              END-IF
           END-IF
           PERFORM PICK-CHANNEL-AND-AMOUNT
           PERFORM APPLY-FRAUD-PATTERN
           PERFORM APPLY-MULE-PATTERN
           PERFORM VALIDATE-AND-POST.

       PICK-CHANNEL-AND-AMOUNT.
           EVALUATE FUNCTION MOD(TXN-NO, 6)
              WHEN 0
                 MOVE "UPI" TO CHANNEL
                 COMPUTE AMOUNT = 50 + FUNCTION MOD(TXN-NO * 73, 25000)
                 MOVE "UPI customer transfer" TO DESCRIPTION
              WHEN 1
                 MOVE "IMPS" TO CHANNEL
                 COMPUTE AMOUNT = 500 + FUNCTION MOD(TXN-NO * 89, 150000)
                 MOVE "IMPS transfer" TO DESCRIPTION
              WHEN 2
                 MOVE "SALARY" TO CHANNEL
                 COMPUTE AMOUNT = 25000 + FUNCTION MOD(TXN-NO * 97,
                    175000)
                 MOVE "Salary credit" TO DESCRIPTION
              WHEN 3
                 MOVE "MERCHANT" TO CHANNEL
                 COMPUTE AMOUNT = 100 + FUNCTION MOD(TXN-NO * 53, 75000)
                 MOVE "Merchant payment" TO DESCRIPTION
              WHEN 4
                 MOVE "NEFT" TO CHANNEL
                 COMPUTE AMOUNT = 1000 + FUNCTION MOD(TXN-NO * 191,
                    300000)
                 MOVE "NEFT transfer" TO DESCRIPTION
              WHEN OTHER
                 MOVE "TRANSFER" TO CHANNEL
                 COMPUTE AMOUNT = 100 + FUNCTION MOD(TXN-NO * 41, 50000)
                 MOVE "Normal transfer" TO DESCRIPTION
           END-EVALUATE.

       APPLY-FRAUD-PATTERN.
           EVALUATE TRUE
              WHEN FUNCTION MOD(TXN-NO, 997) = 0
                 MOVE 1 TO FRAUD-FLAG
                 MOVE "DORMANCY_BREAK" TO FRAUD-TYPE
                 MOVE "Dormancy break transaction" TO DESCRIPTION
                 COMPUTE AMOUNT = 10000 + FUNCTION MOD(TXN-NO, 90000)
              WHEN FUNCTION MOD(TXN-NO, 809) = 0
                 MOVE 1 TO FRAUD-FLAG
                 MOVE "RAPID_IN_OUT" TO FRAUD-TYPE
                 MOVE "Rapid in/out transfer" TO DESCRIPTION
                 COMPUTE AMOUNT = 45000 + FUNCTION MOD(TXN-NO, 50000)
              WHEN FUNCTION MOD(TXN-NO, 673) = 0
                 MOVE 1 TO FRAUD-FLAG
                 MOVE "NIGHT_TRANSACTION" TO FRAUD-TYPE
                 MOVE "Night transaction" TO DESCRIPTION
              WHEN FUNCTION MOD(TXN-NO, 541) = 0
                 MOVE 1 TO FRAUD-FLAG
                 MOVE "STRUCTURED_SPLITTING" TO FRAUD-TYPE
                 MOVE "Structured splitting" TO DESCRIPTION
                 COMPUTE AMOUNT = 9900
              WHEN FUNCTION MOD(TXN-NO, 431) = 0
                 MOVE 1 TO FRAUD-FLAG
                 MOVE "VELOCITY_SPIKE" TO FRAUD-TYPE
                 MOVE "Velocity spike" TO DESCRIPTION
           END-EVALUATE.

       APPLY-MULE-PATTERN.
           EVALUATE TRUE
              WHEN FUNCTION MOD(TXN-NO, 701) = 0
                 MOVE 1 TO MULE-FLAG
                 MOVE "FAN_OUT" TO PATTERN-TYPE
                 COMPUTE SENDER-NUM = FUNCTION MOD(TXN-NO * 811,
                    WS-MAX-ACCOUNTS) + 1
                 COMPUTE RECEIVER-NUM = FUNCTION MOD(TXN-NO * 811 +
                    WORKER-ID * 37, WS-MAX-ACCOUNTS) + 1
                 MOVE "Fan-out mule movement" TO DESCRIPTION
              WHEN FUNCTION MOD(TXN-NO, 887) = 0
                 MOVE 1 TO MULE-FLAG
                 MOVE "RELAY" TO PATTERN-TYPE
                 COMPUTE RECEIVER-NUM = FUNCTION MOD(SENDER-NUM + 17,
                    WS-MAX-ACCOUNTS) + 1
                 MOVE "Relay mule chain movement" TO DESCRIPTION
              WHEN FUNCTION MOD(TXN-NO, 929) = 0
                 MOVE 1 TO MULE-FLAG
                 MOVE "LAYERING" TO PATTERN-TYPE
                 COMPUTE RECEIVER-NUM = FUNCTION MOD(SENDER-NUM + 29,
                    WS-MAX-ACCOUNTS) + 1
                 MOVE "Layering mule movement" TO DESCRIPTION
           END-EVALUATE.

       VALIDATE-AND-POST.
           IF CHANNEL = "SALARY"
              MOVE 1 TO SENDER-NUM
           END-IF
           IF ACCOUNT-BALANCES(SENDER-NUM) < AMOUNT
              MOVE "REJECTED" TO TXN-STATUS
           ELSE
              MOVE "COMPLETED" TO TXN-STATUS
              SUBTRACT AMOUNT FROM ACCOUNT-BALANCES(SENDER-NUM)
              ADD AMOUNT TO ACCOUNT-BALANCES(RECEIVER-NUM)
           END-IF
           PERFORM BUILD-TXN-FIELDS
           CALL "db_insert_transaction" USING
                BY REFERENCE TXN-ID LEN-24
                BY REFERENCE TIMESTAMP LEN-24
                BY REFERENCE SENDER-ID LEN-16
                BY REFERENCE RECEIVER-ID LEN-16
                BY REFERENCE AMOUNT
                BY REFERENCE CHANNEL LEN-16
                BY REFERENCE TXN-STATUS LEN-16
                BY REFERENCE FRAUD-FLAG
                BY REFERENCE MULE-FLAG
                BY REFERENCE DESCRIPTION LEN-128
                BY REFERENCE DB-RESULT
           IF TXN-STATUS = "COMPLETED"
              COMPUTE NEW-BALANCE = ACCOUNT-BALANCES(SENDER-NUM)
              MOVE SENDER-ID TO ACCOUNT-ID
              CALL "db_update_balance" USING
                   BY REFERENCE ACCOUNT-ID LEN-16
                   BY REFERENCE NEW-BALANCE
                   BY REFERENCE DB-RESULT
              COMPUTE NEW-BALANCE = ACCOUNT-BALANCES(RECEIVER-NUM)
              MOVE RECEIVER-ID TO ACCOUNT-ID
              CALL "db_update_balance" USING
                   BY REFERENCE ACCOUNT-ID LEN-16
                   BY REFERENCE NEW-BALANCE
                   BY REFERENCE DB-RESULT
           END-IF
           IF FRAUD-FLAG = 1
              PERFORM INSERT-FRAUD-EVENT
           END-IF.

       INSERT-FRAUD-EVENT.
           STRING "FRD" DELIMITED BY SIZE
                  TXN-NUM-TEXT DELIMITED BY SIZE
                  INTO EVENT-ID
           END-STRING
           MOVE "HIGH" TO SEVERITY
           CALL "db_insert_fraud_event" USING
                BY REFERENCE EVENT-ID LEN-24
                BY REFERENCE TXN-ID LEN-24
                BY REFERENCE SENDER-ID LEN-16
                BY REFERENCE FRAUD-TYPE LEN-48
                BY REFERENCE DESCRIPTION LEN-128
                BY REFERENCE SEVERITY LEN-16
                BY REFERENCE TIMESTAMP LEN-24
                BY REFERENCE DB-RESULT.

       BUILD-TXN-FIELDS.
           MOVE TXN-NO TO TXN-NUM-TEXT
           STRING "TXN" DELIMITED BY SIZE
                  TXN-NUM-TEXT DELIMITED BY SIZE
                  INTO TXN-ID
           END-STRING
           MOVE SENDER-NUM TO SOURCE-NUM
           PERFORM BUILD-LINKED-ID
           MOVE LINKED-ID TO SENDER-ID
           MOVE RECEIVER-NUM TO SOURCE-NUM
           PERFORM BUILD-LINKED-ID
           MOVE LINKED-ID TO RECEIVER-ID
           PERFORM BUILD-TIMESTAMP.

       BUILD-ACCOUNT-ID.
           MOVE I TO ACCT-NUM-TEXT
           MOVE SPACES TO ACCOUNT-ID
           STRING "ACC" DELIMITED BY SIZE
                  ACCT-NUM-TEXT DELIMITED BY SIZE
                  INTO ACCOUNT-ID
           END-STRING.

       BUILD-MULE-ACCOUNT-ID.
           MOVE MULE-NUM TO ACCT-NUM-TEXT
           MOVE SPACES TO ACCOUNT-ID
           STRING "ACC" DELIMITED BY SIZE
                  ACCT-NUM-TEXT DELIMITED BY SIZE
                  INTO ACCOUNT-ID
           END-STRING.

       BUILD-LINKED-ID.
           MOVE SOURCE-NUM TO ACCT-NUM-TEXT
           MOVE SPACES TO LINKED-ID
           STRING "ACC" DELIMITED BY SIZE
                  ACCT-NUM-TEXT DELIMITED BY SIZE
                  INTO LINKED-ID
           END-STRING.

       BUILD-CHAIN-ID.
           MOVE CHAIN-NUM TO CHAIN-NUM-TEXT
           STRING "CHAIN" DELIMITED BY SIZE
                  CHAIN-NUM-TEXT DELIMITED BY SIZE
                  INTO CHAIN-ID
           END-STRING.

       PICK-OCCUPATION.
           EVALUATE FUNCTION MOD(I, 6)
              WHEN 0 MOVE "SALARIED" TO OCCUPATION
              WHEN 1 MOVE "SELF_EMPLOYED" TO OCCUPATION
              WHEN 2 MOVE "STUDENT" TO OCCUPATION
              WHEN 3 MOVE "RETIRED" TO OCCUPATION
              WHEN 4 MOVE "MERCHANT" TO OCCUPATION
              WHEN OTHER MOVE "PROFESSIONAL" TO OCCUPATION
           END-EVALUATE.

       BUILD-TIMESTAMP.
           ACCEPT DATE-YYYYMMDD FROM DATE YYYYMMDD
           ACCEPT TIME-HHMMSS FROM TIME
           MOVE DATE-YYYYMMDD TO DATE-TEXT
           MOVE TIME-HHMMSS TO TIME-TEXT
           MOVE DATE-TEXT(1:4) TO TS-YEAR
           MOVE DATE-TEXT(5:2) TO TS-MONTH
           MOVE DATE-TEXT(7:2) TO TS-DAY
           MOVE TIME-TEXT(1:2) TO TS-HOUR
           MOVE TIME-TEXT(3:2) TO TS-MIN
           MOVE TIME-TEXT(5:2) TO TS-SEC
           MOVE SPACES TO TIMESTAMP
           STRING TS-YEAR DELIMITED BY SIZE
                  "-" DELIMITED BY SIZE
                  TS-MONTH DELIMITED BY SIZE
                  "-" DELIMITED BY SIZE
                  TS-DAY DELIMITED BY SIZE
                  "T" DELIMITED BY SIZE
                  TS-HOUR DELIMITED BY SIZE
                  ":" DELIMITED BY SIZE
                  TS-MIN DELIMITED BY SIZE
                  ":" DELIMITED BY SIZE
                  TS-SEC DELIMITED BY SIZE
                  INTO TIMESTAMP
           END-STRING.

       SET-FINISHED.
           MOVE "status" TO CONTROL-KEY
           IF STOP-RESULT = 1
              MOVE "stopped" TO CONTROL-VALUE
           ELSE
              MOVE "finished" TO CONTROL-VALUE
           END-IF
           CALL "db_update_sim_control" USING
                BY REFERENCE CONTROL-KEY LEN-32
                BY REFERENCE CONTROL-VALUE LEN-32
                BY REFERENCE DB-RESULT
           PERFORM BUILD-TIMESTAMP
           MOVE "INFO" TO LOG-LEVEL
           MOVE "COBOL banking engine finished" TO LOG-MESSAGE
           CALL "db_insert_log" USING
                BY REFERENCE LOG-LEVEL LEN-16
                BY REFERENCE LOG-MESSAGE LEN-128
                BY REFERENCE TIMESTAMP LEN-24
                BY REFERENCE DB-RESULT.
