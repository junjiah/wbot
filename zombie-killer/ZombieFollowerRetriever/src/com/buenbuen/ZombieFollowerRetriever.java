package com.buenbuen;

import org.apache.commons.cli.CommandLine;
import org.apache.commons.cli.CommandLineParser;
import org.apache.commons.cli.DefaultParser;
import org.apache.commons.cli.HelpFormatter;
import org.apache.commons.cli.Option;
import org.apache.commons.cli.Options;
import org.apache.commons.cli.ParseException;
import org.codehaus.jackson.map.ObjectMapper;

import java.io.File;
import java.io.IOException;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;

import weibo4j.Friendships;
import weibo4j.model.UserWapper;
import weibo4j.model.WeiboException;


public class ZombieFollowerRetriever {

  public static void main(String[] args) throws IOException {

    // Parsing command line arguments.
    Options cmdOptions = new Options();

    Option dbPathOption = new Option("d", "database", true, "SQLite DB file path");
    dbPathOption.setRequired(true);
    Option configPathOption = new Option("c", "config", true, "Config JSON");
    configPathOption.setRequired(true);

    cmdOptions.addOption(dbPathOption);
    cmdOptions.addOption(configPathOption);

    CommandLineParser parser = new DefaultParser();
    HelpFormatter formatter = new HelpFormatter();
    CommandLine cmd;
    try {
      cmd = parser.parse(cmdOptions, args);
    } catch (ParseException e) {
      System.err.println(e.getMessage());
      formatter.printHelp(
          "java -jar ZombieCleaner.jar -d /path/to/sqlite/db -c /path/to/config/json",
          cmdOptions);
      System.exit(1);
      return;
    }

    // Read config.
    Map config = readConfigJSON(cmd.getOptionValue("config"));
    // Config should have access token and UID.
    String accessToken = (String) config.get("accessToken");
    String uid = (String) config.get("uid");
    if (accessToken == null || uid == null) {
      System.err.println("Access token or UID not specified in config.");
      System.exit(1);
      return;
    }
    final int followersToRetrieve = (int) config.getOrDefault("followersToRetrieve", 1000);
    final int scheduledIntervalInMinutes = (int) config.getOrDefault("scheduledIntervalInMinutes", 5);

    // Init DB model with file path.
    FollowerModel.setDBPath(cmd.getOptionValue("database"));

    // Schedule jobs.
    ScheduledExecutorService executor = Executors.newScheduledThreadPool(1);
    Runnable task = () -> {
      Friendships friendships = new Friendships(accessToken);
      Optional<String[]> ids = Optional.empty();

      try {
        UserWapper users = friendships.getFollowersById(uid);
        int total = (int) users.getTotalNumber();
        System.out.println("Total follower: " + total);

        String[] uids = friendships.getFollowersIdsById(uid, followersToRetrieve, 0);
        System.out.println("Fetched follower: " + uids.length);

        ids = Optional.of(uids);
      } catch (WeiboException e) {
        e.printStackTrace();
        return;
      }

      ids.ifPresent(FollowerModel::insertFollowerIDs);
    };
    executor.scheduleWithFixedDelay(task, 0, scheduledIntervalInMinutes, TimeUnit.MINUTES);
  }

  private static Map readConfigJSON(String configPath) throws IOException {
    ObjectMapper objectMapper = new ObjectMapper();
    return objectMapper.readValue(new File(configPath), Map.class);
  }
}
