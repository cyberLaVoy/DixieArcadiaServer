import os
import psycopg2
import psycopg2.extras
import urllib.parse

class GamesDB:

    def __init__(self):
        urllib.parse.uses_netloc.append("postgres")
        url = urllib.parse.urlparse(os.environ["DATABASE_URL"])

        self.connection = psycopg2.connect(
            cursor_factory=psycopg2.extras.RealDictCursor,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            host=url.hostname,
            port=url.port
        )
        self.cursor = self.connection.cursor()

    def __del__(self):
        self.connection.close()

    def createTables(self):
        usersTable = "CREATE TABLE IF NOT EXISTS users ( profile_name varchar, encrypted_password varchar);"
        adminsTable = "CREATE TABLE IF NOT EXISTS admins ( profile_name varchar NOT NULL UNIQUE );"
        gamesTable = "CREATE TABLE IF NOT EXISTS games ( id integer PRIMARY KEY, profile_name varchar, description varchar, game_name varchar, last_played integer DEFAULT NULL, plays integer DEFAULT 0, zip, thumbnail);"
        tagsTable = "CREATE TABLE IF NOT EXISTS tags ( game_id integer, tag varchar );"
        ratingsTable = "CREATE TABLE IF NOT EXISTS ratings ( game_id integer, thumb_up varchar, thumb_down varchar );"

        self.cursor.execute(usersTable)
        self.cursor.execute(adminsTable)
        self.cursor.execute(gamesTable)
        self.cursor.execute(tagsTable)
        self.cursor.execute(ratingsTable)
        self.connection.commit()

    # adds the client as a user and an admin
    def addClientUser(self):
        clientUserName = "client"
        clientPassword = "Over8the8misty8mountain!@"
        if not self.checkProfileName(clientUserName):
            clientInsert = "INSERT INTO users (profile_name, encrypted_password) VALUES (?,?)"
            toAdmin = "INSERT INTO admins (profile_name) VALUES (?)"
            #encrypted_password = bcrypt.encrypt(clientPassword)
            encrypted_password = clientPassword
            self.cursor.execute(clientInsert, (clientUserName, encrypted_password))
            self.cursor.execute(toAdmin, (clientUserName,))
            self.connection.commit()


# Game Methods
    def createGame(self, profile_name, game_name, description):
        sql = "INSERT INTO games (profile_name, game_name, description) VALUES (?,?,?)"
        vals = (profile_name, game_name, description)
        self.cursor.execute(sql, vals)
        self.connection.commit()
        return self.cursor.lastrowid 

    def updateGameInfo(self, game_id, game_name, description, tags):
        sql = "UPDATE games SET game_name = ?, description = ? WHERE id = ?"
        vals = (game_name, description, game_id)
        self.cursor.execute(sql, vals)
        self.connection.commit()
        # delete all exsiting tags and add the new tags
        self.deleteGameTags(game_id)
        for tag in tags:
            self.addTag(game_id, tag)
    def setGameThumnail(self, game_id, thumnail):
        sql = "UPDATE games SET thumbnail = ? WHERE id = ?"
        vals = (thumnail, game_id)
        self.cursor.execute(sql, vals)
        self.connection.commit()
    def setGameZip(self, game_id, zip):
        sql = "UPDATE games SET zip = ? WHERE id = ?"
        vals = (zip, game_id)
        self.cursor.execute(sql, vals)
        self.connection.commit()

    def incrementPlays(self, game_id):
        sql = "SELECT plays FROM games WHERE id=?"
        self.cursor.execute(sql, (game_id,))
        rows = self.cursor.fetchall()
        plays = rows[0]["plays"]
        plays += 1
        sql = "UPDATE games SET plays = ? WHERE id = ?"
        self.cursor.execute(sql, (plays, game_id))
        self.connection.commit()

    def deleteGame(self, id):
        sql = "DELETE FROM games WHERE id=?"
        self.cursor.execute(sql, (id,))
        self.connection.commit()
        sql = "DELETE FROM tags WHERE game_id=?"
        self.cursor.execute(sql, (id,))
        self.connection.commit()
        sql = "DELETE FROM ratings WHERE game_id=?"
        self.cursor.execute(sql, (id,))
        self.connection.commit()

    def listGames(self):
        sql = "SELECT id, profile_name, game_name, description, last_played, plays FROM games"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        self.addTagsAndRatings(rows)
        return rows

    def listTop20Games(self):
        query = "SELECT id, profile_name, game_name, description, last_played, plays FROM games ORDER BY plays DESC LIMIT 20"
        self.cursor.execute(query)
        rows = self.cursor.fetchall()
        self.addTagsAndRatings(rows)
        return rows

    def listGamesWithGeneralFilter(self, profile_name, game_name, description):
        sql = "SELECT id, profile_name, game_name, description, last_played, plays FROM games WHERE profile_name LIKE ? AND description LIKE ? AND game_name LIKE ?"
        # Add wild cards to the parsed input
        vals = ('%'+profile_name+'%', '%'+description+'%', '%'+game_name+'%')
        self.cursor.execute(sql, vals)
        rows = self.cursor.fetchall()
        self.addTagsAndRatings(rows)
        return rows
    def listGamesWithTagsFilter(self, tag):
        query = "SELECT id, profile_name, game_name, description, last_played, plays FROM games WHERE id IN (SELECT game_id FROM tags WHERE tag = ?)"
        self.cursor.execute(query, (tag,))
        rows = self.cursor.fetchall()
        self.addTagsAndRatings(rows)
        return rows

    def getGameInfo(self, id):
        sql = "SELECT id, profile_name, game_name, description, last_played, plays FROM games WHERE games.id = ?"
        self.cursor.execute(sql,(id,))  
        gameInfo = self.cursor.fetchall()
        self.addTagsAndRatings(gameInfo)
        return gameInfo
    def getGameZip(self, id):
        sql = "SELECT zip FROM games WHERE games.id = ?"
        self.cursor.execute(sql,(id,))
        zip = self.cursor.fetchone()
        return zip
    def getGameThumnail(self, id):
        sql = "SELECT thumbnail FROM games WHERE games.id = ?"
        self.cursor.execute(sql,(id,))
        thumbnail = self.cursor.fetchone()
        return thumbnail
    def gameExists(self, game_id):
        sql = "SELECT game_name FROM games WHERE id = ?"
        self.cursor.execute(sql, (game_id,))
        rows = self.cursor.fetchone()
        return rows is not None

# Tags Methods
    def addTag(self, game_id, tag):
        sql = "INSERT INTO tags (game_id, tag) VALUES (?,?)"
        tag = tag.upper()
        self.cursor.execute(sql, (game_id, tag))
        self.connection.commit()
    def deleteTag(self, game_id, tag):
        tag = tag.upper()
        sql = "DELETE FROM tags WHERE game_id = ? AND tag = ?"
        self.cursor.execute(sql, (game_id, tag))
        self.connection.commit()
    def deleteGameTags(self, game_id):
        sql = "DELETE FROM tags WHERE game_id = ?"
        self.cursor.execute(sql, (game_id,))
        self.connection.commit()
    def getGameTags(self, id):
        sql = "SELECT tag FROM tags WHERE game_id = ?"
        self.cursor.execute(sql, (id,))
        rows = self.cursor.fetchall()
        tags = []
        for tag in rows:
            tags.append(tag["tag"])
        return tags
    def getDistinctTags(self):
        sql = "SELECT DISTINCT tag FROM tags"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        tags = []
        for tag in rows:
            tags.append(tag["tag"])
        return tags


# Ratings Methods
    def addRating(self, game_id, thumbUp, thumbDown):
        sql = "INSERT INTO ratings (game_id, thumb_up, thumb_down) VALUES (?,?,?)"
        self.cursor.execute(sql, (game_id, thumbUp, thumbDown))
        self.connection.commit()
    def getRatings(self, game_id):
        sql = "SELECT * FROM ratings WHERE game_id = ?"
        self.cursor.execute(sql, (game_id,))
        rows = self.cursor.fetchall()
        thumbs_up = 0
        thumbs_down = 0
        for rating in rows:
            if rating["thumb_down"] == "true":
                thumbs_down += 1
            elif rating["thumb_up"] == "true":
                thumbs_up += 1
        ratings = {"up": thumbs_up, "down": thumbs_down}
        return ratings


#Roles Methods
    def addAdmin(self, profile_name):
        sql = "INSERT INTO admins (profile_name) VALUES (?)"
        self.cursor.execute(sql, (profile_name,))
        self.connection.commit()
    def removeAdmin(self, profile_name):
        sql = "DELETE FROM admins WHERE profile_name = ?"
        self.cursor.execute(sql, (profile_name,))
        self.connection.commit()
    def isAdmin(self, profile_name):
        sql = "SELECT profile_name FROM admins WHERE profile_name = ?"
        self.cursor.execute(sql, (profile_name,))
        rows = self.cursor.fetchone()
        return rows is not None

# USERS operations
    def createUser(self, profile_name, encrypted_password):
        Query = "INSERT INTO users (profile_name, encrypted_password) VALUES (?, ?)"
        self.cursor.execute(Query, (profile_name, encrypted_password))
        self.connection.commit()
    def getUserAuthInfo(self, profile_name):
        Query = "SELECT rowid, encrypted_password FROM users WHERE profile_name = ?"
        self.cursor.execute(Query, (profile_name,))
        user = self.cursor.fetchall()
        return user
    def getUser(self, ID):
        Query = "SELECT profile_name FROM users WHERE rowid = ?"
        self.cursor.execute(Query, (ID,))
        user = self.cursor.fetchall()
        return user
    def checkProfileName(self, profile_name):
        self.cursor.execute("SELECT profile_name FROM users WHERE profile_name = ?", (profile_name,))
        profileNames = self.cursor.fetchall()
        taken = False
        if len(profileNames) > 0:
            taken = True
        return taken
    def profileNameOwnsGame(self, profile_name, game_id):
        query = "SELECT game_name FROM games WHERE profile_name = ? AND id = ?" 
        self.cursor.execute(query, (profile_name, game_id))
        row = self.cursor.fetchone()
        return row is not None


# General operations
    def addTagsAndRatings(self, gamesData):
        for obj in gamesData:
            tagsList = self.getGameTags(obj["id"])
            ratings = self.getRatings(obj["id"])
            obj["ratings"] = ratings
            obj["tags"] = tagsList

