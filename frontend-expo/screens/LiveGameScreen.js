import React from 'react';
import { View, Image, Text, StyleSheet } from 'react-native';

export default function LiveGameScreen({ route }) {
  const { homeTeamCode, awayTeamCode, gameId } = route.params;

  return (
    <View style={styles.container}>
      <View style={styles.teamContainer}>
        <Text style={styles.label}>{awayTeamCode}</Text>
      </View>
      <Text style={styles.vs}>VS</Text>
      <View style={styles.teamContainer}>
        <Text style={styles.label}>{homeTeamCode}</Text>
      </View>
      <Text style={{ marginTop: 20 }}>GameId: {gameId}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginTop: 80,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
  },
  teamContainer: {
    alignItems: 'center',
    marginHorizontal: 20,
  },
  logo: {
    width: 80,
    height: 80,
    resizeMode: 'contain',
  },
  label: {
    marginTop: 8,
    fontSize: 16,
    fontWeight: '600',
  },
  vs: {
    fontSize: 22,
    fontWeight: '700',
    marginHorizontal: 10,
  },
});
