package com.buenbuen;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;

public class FollowerModel {

  public static final String INSERT_SQL_TEMPLATE = "INSERT OR IGNORE INTO follower (uid, state) VALUES(?, 'new')";

  private static String dbConnPath;


  private FollowerModel() { /* Disallow instantiation. */ }

  public static void setDBPath(String dbPath) {
    dbConnPath = "jdbc:sqlite:" + dbPath;
  }

  public static void insertFollowerIDs(String[] uids) {
    if (uids.length == 0) {
      return;
    }

    try {
      Connection conn = DriverManager.getConnection(dbConnPath);
      conn.setAutoCommit(false);

      PreparedStatement preparedStatement = conn.prepareStatement(INSERT_SQL_TEMPLATE);
      preparedStatement.setQueryTimeout(30);
      for (String uid : uids) {
        preparedStatement.setString(1, uid);
        preparedStatement.addBatch();
      }
      preparedStatement.executeBatch();

      conn.commit();
    } catch (SQLException e) {
      System.err.println(e.getMessage());
    }
  }
}
