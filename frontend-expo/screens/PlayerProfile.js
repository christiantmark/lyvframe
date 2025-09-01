import React, { useState, useEffect } from "react";
import { View, Text, Image, StyleSheet, ActivityIndicator, ScrollView } from "react-native";

// Helper to convert "PT34M13.00S" => "34:13"
function formatMinutes(duration) {
  if (!duration) return "0:00";
  const match = duration.match(/PT(\d+)M(\d+)(?:\.\d+)?S/);
  if (!match) return "0:00";

  const minutes = parseInt(match[1], 10);
  const seconds = parseInt(match[2], 10);

  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export default function PlayerProfile({ route }) {
  const { player, gameId } = route.params;

  const [playerNameMap, setPlayerNameMap] = useState({});
  const [playerStats, setPlayerStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [imageError, setImageError] = useState(false);

  const playerId = player.personId || player.id || "2544";

  // Fetch player map
  useEffect(() => {
    fetch("https://lyvframe.com/nba/player_map?client_id=be3c14f8-c257-48f0-becd-0fa0c367f6aa")
      .then((res) => res.json())
      .then((data) => setPlayerNameMap(data))
      .catch((err) => console.error("Failed to fetch player map:", err));
  }, []);

  // Fetch player stats for this game
  useEffect(() => {
    if (!playerId || !gameId) return;

    const fetchStats = async () => {
      try {
        const res = await fetch(`https://lyvframe.com/nba/player_stats?gameId=${gameId}&playerId=${playerId}`);
        if (!res.ok) throw new Error(`Status ${res.status}`);
        const data = await res.json();
        setPlayerStats(data);
      } catch (err) {
        console.error("Failed to fetch player stats:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [playerId, gameId]);

  if (loading) {
    return <ActivityIndicator size="large" color="black" style={{ flex: 1 }} />;
  }

  const fullName = playerNameMap[playerId] || player.name || "Unknown Player";

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Image
        source={{
          uri: imageError
            ? "https://cdn-icons-png.flaticon.com/512/149/149071.png"
            : `https://cdn.nba.com/headshots/nba/latest/1040x760/${playerId}.png`,
        }}
        style={styles.headshot}
        resizeMode="contain"
        onError={() => setImageError(true)}
      />
      <Text style={styles.name}>{fullName}</Text>
      <Text style={styles.id}>ID: {playerId}</Text>

      {playerStats ? (
        <View style={styles.statsContainer}>
          <Text style={styles.statText}>Team: {playerStats.team}</Text>
          <Text style={styles.statText}>Position: {playerStats.position}</Text>
          <Text style={styles.statText}>Jersey: {playerStats.jerseyNum}</Text>
          <Text style={styles.statText}>Minutes: {formatMinutes(playerStats.minutes)}</Text>
          <Text style={styles.statText}>Points: {playerStats.points}</Text>
          <Text style={styles.statText}>Rebounds: {playerStats.rebounds}</Text>
          <Text style={styles.statText}>Assists: {playerStats.assists}</Text>
          <Text style={styles.statText}>Steals: {playerStats.steals}</Text>
          <Text style={styles.statText}>Blocks: {playerStats.blocks}</Text>
          <Text style={styles.statText}>Turnovers: {playerStats.turnovers}</Text>
          <Text style={styles.statText}>
            FG: {playerStats.fgMade}/{playerStats.fgAttempted} ({(playerStats.fgPct*100).toFixed(1)}%)
          </Text>
          <Text style={styles.statText}>
            3PT: {playerStats.threePtMade}/{playerStats.threePtAttempted} ({(playerStats.threePtPct*100).toFixed(1)}%)
          </Text>
          <Text style={styles.statText}>
            FT: {playerStats.ftMade}/{playerStats.ftAttempted} ({(playerStats.ftPct*100).toFixed(1)}%)
          </Text>
        </View>
      ) : (
        <Text style={styles.noStats}>No stats available</Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 20,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "flex-start",
  },
  headshot: {
    width: 200,
    height: 200,
    marginBottom: 20,
    borderRadius: 10,
    backgroundColor: "#222",
  },
  name: {
    fontSize: 24,
    fontWeight: "bold",
    color: "white",
  },
  id: {
    fontSize: 16,
    color: "gray",
    marginBottom: 20,
  },
  statsContainer: {
    width: "100%",
    marginTop: 10,
    backgroundColor: "#1a1a1a",
    padding: 12,
    borderRadius: 10,
  },
  statText: {
    color: "white",
    fontSize: 14,
    marginVertical: 2,
  },
  noStats: {
    color: "gray",
    marginTop: 10,
  },
});
