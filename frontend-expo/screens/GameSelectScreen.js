import React, { useState } from 'react';
import { View, Text, Button, FlatList, TouchableOpacity } from 'react-native';
import { fetchGamesByDate } from '../api/flaskAPI';
import axios from 'axios';
import ScrollableDatePicker from '../components/ScrollableDatePicker'; // import the new picker

const TEST_CLIENT_ID = 'be3c14f8-c257-48f0-becd-0fa0c367f6aa';

export default function GameSelectScreen({ navigation }) {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [games, setGames] = useState([]);
  const [selectedGame, setSelectedGame] = useState(null);
  const [loading, setLoading] = useState(false);
  const teamNameToCode = {
    'Atlanta Hawks': 'ATL',
    'Boston Celtics': 'BOS',
    'Brooklyn Nets': 'BKN',
    'Charlotte Hornets': 'CHA',
    'Chicago Bulls': 'CHI',
    'Cleveland Cavaliers': 'CLE',
    'Dallas Mavericks': 'DAL',
    'Denver Nuggets': 'DEN',
    'Detroit Pistons': 'DET',
    'Golden State Warriors': 'GSW',
    'Houston Rockets': 'HOU',
    'Indiana Pacers': 'IND',
    'Los Angeles Clippers': 'LAC',
    'Los Angeles Lakers': 'LAL',
    'Memphis Grizzlies': 'MEM',
    'Miami Heat': 'MIA',
    'Milwaukee Bucks': 'MIL',
    'Minnesota Timberwolves': 'MIN',
    'New Orleans Pelicans': 'NOP',
    'New York Knicks': 'NYK',
    'Oklahoma City Thunder': 'OKC',
    'Orlando Magic': 'ORL',
    'Philadelphia 76ers': 'PHI',
    'Phoenix Suns': 'PHX',
    'Portland Trail Blazers': 'POR',
    'Sacramento Kings': 'SAC',
    'San Antonio Spurs': 'SAS',
    'Toronto Raptors': 'TOR',
    'Utah Jazz': 'UTA',
    'Washington Wizards': 'WAS'
  };


  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const handleFetchGames = async () => {
    const dateStr = formatDate(selectedDate);
    console.log('Fetching games for:', dateStr);
    setLoading(true);
    try {
      const data = await fetchGamesByDate(dateStr, TEST_CLIENT_ID);
      setGames(data || []);
      setSelectedGame(null);
    } catch (err) {
      console.error('Error loading games:', err);
      setGames([]);
    } finally {
      setLoading(false);
    }
  };

  const handleStartWatching = async () => {
    if (!selectedGame) return;

    const homeCode = selectedGame.homeTeam;
    const awayCode = selectedGame.awayTeam;

    try {
      const url = `https://lyvframe.com/nba/select_game?gameId=${selectedGame.gameId}&client_id=${TEST_CLIENT_ID}`;
      await axios.get(url);
      console.log('Successfully selected game');

      navigation.navigate("Watching", {
        homeTeamCode: homeCode,
        awayTeamCode: awayCode,
        gameId: selectedGame.gameId, // ✅ THIS LINE WAS MISSING
        clientId: TEST_CLIENT_ID,
      });
    } catch (err) {
      console.error('Failed to select game:', err);
    }
  };

  return (
    <View style={{ flex: 1, padding: 20 }}>
      <Text style={{ fontSize: 22, fontWeight: 'bold' }}>Select a Game Date</Text>

      {/* Here’s the new scrollable picker */}
      <ScrollableDatePicker
        initialDate={selectedDate}
        onDateChange={setSelectedDate}
      />

      <Text style={{ marginTop: 10 }}>
        Selected: {formatDate(selectedDate)}
      </Text>

      <Button title="Load Games" onPress={handleFetchGames} />

      {loading && <Text style={{ marginTop: 10 }}>Loading games...</Text>}

      <FlatList
        data={games}
        keyExtractor={(item) => item.gameId}
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() => setSelectedGame(item)}
            style={{
              padding: 10,
              borderBottomWidth: 1,
              backgroundColor: selectedGame?.gameId === item.gameId ? '#d3f3ff' : 'white',
            }}
          >
            <Text>{item.awayTeam} @ {item.homeTeam}</Text>
          </TouchableOpacity>
        )}
        style={{ marginTop: 20 }}
      />

      {selectedGame && (
        <View style={{ marginTop: 20 }}>
          <Button title="Start Watching" onPress={handleStartWatching} />
        </View>
      )}
    </View>
  );
}
