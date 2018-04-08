# Dixie Arcadia RESTful API Documentation

## Dependancies:
#### Python version:
* python 3.6
#### Python libraries:
* sqlite3
* http
* urllib
* passlib
* json
* time
* base64
* os
#### Required database:
* sqlite3

## Initializing server:
#### From command line: 
```
python3 server.py
```

## Resources:
#### games
##### Attributes:
* id (integer)
* profile_name (varchar)
* description (varchar)
* game_name (varchar)
* last_played (integer)
* plays (integer)
* zip (blob)
* thumbnail (blob)

#### tags
##### Attributes:
* game_id (integer)
* tag (varchar)

#### ratings
##### Attributes:
* game_id (integer)
* thumb_up (varchar) "true" or "false"
* thumb_down (varchar) "true" or "false"

#### users
##### Attributes:
* profile_name (varchar)
* encrypted_password (varchar)

#### admins
##### Attributes:
* profile_name (varchar) present if admin

#### sessions
##### Attributes:
* rowid (from users table, when authenticated)
* isAdmin (if profile name in admins table)
* any temporary data


## Database Schema:
```SQL
CREATE TABLE IF NOT EXISTS games 
( id integer PRIMARY KEY AUTOINCREMENT, 
profile_name varchar, 
description varchar, 
game_name varchar, 
last_played integer 
DEFAULT NULL, 
plays integer DEFAULT 0, 
zip blob, 
thumbnail blob );

CREATE TABLE IF NOT EXISTS tags 
( game_id integer, tag varchar );

CREATE TABLE IF NOT EXISTS ratings
( game_id integer, 
thumb_up varchar, 
thumb_down varchar );

CREATE TABLE IF NOT EXISTS users 
( profile_name varchar, 
encrypted_password varchar);

CREATE TABLE IF NOT EXISTS admins 
( profile_name varchar NOT NULL UNIQUE );
```

## REST Endpoints:
#### note that bool is "true" or "false"
Name | HTTP Method | Path | Expected Body (x-www-form-urlencoded) | Query String Options
------------ | ------------- | ------------- | ------------ | --------------
List | GET | /games |  | tags_contain, profile_name_contains, description_contains, game_name_contains, most_popular (bool)
List | GET | /games/tags |  |
List | GET | /me/games |  | 
Retrieve | GET | /games/id |  | zip (bool), thumbnail (bool)
Retrieve | GET | games/game_id/ratings |  | 
Retrieve | GET | games/game_id/tags |  | 
Retrieve | GET | /me | | 
Create | POST | /games | game_name, description, tags (each tag as value) | 
Create | POST | /tags | game_id, tag | 
Create | POST | /ratings | game_id, thumb_up (bool), thumb_down (bool) | 
Create | POST | /users | profile_name, password | 
Create | POST | /sessions | profile_name, password | 
Replace | PUT | /games/id | (if not zip, thumbnail, or increment) game_name, description, tags | zip (bool), thumbnail (bool), increment_plays (bool)
Delete | DELETE | /games/id |  | 
Delete | DELETE | games/game_id/tags | tag | 
Delete | DELETE | /sessions |  | 


## Password Hashing Method:
#### passlib (bcrypt)
