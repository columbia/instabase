### Instabase

Web app for csds course

#### Objective
- Allow students to upload predictions of their test runs (on the test data set)
- Authentication with UNIs and passwords
- Compute F1 score, precision and recall
- Persist scores and code submission 
- Generate a (real-time?) leaderboard

#### Stack
- Nodejs - [Hapi](http://hapijs.com/)
- Frontend (jquery and the usual)
- RethinkDB (as a DB)
- Websockets 

#### Pages
- Leaderboard
- Login 
- Home (Dashboard)
  - Her previous submissions
  - Upload
    - Matches file upload (take only .csv files)
    - Python code paste 
    
#### Misc Features
- Email password to columbia ID
- Email successful submissions 
