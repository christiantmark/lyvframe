import axios from 'axios';

const BASE_URL = 'https://lyvframe.com';

export const fetchGamesByDate = async (dateStr) => {
  try {
    console.log('Fetching games from:', `${BASE_URL}/nba/games`, {
      date: dateStr,
    });
    const response = await axios.get(`${BASE_URL}/nba/games`, {
      params: {
        date: dateStr,
      },
    });
    return response.data;
  } catch (error) {
    console.error('Failed to fetch games:', error);
    return [];
  }
};


export const getPeekShot = async (clientId) => {
  try {
    console.log("Fetching peek shot for clientId:", clientId);

    if (!clientId || typeof clientId !== 'string' || clientId.length < 10) {
      throw new Error(`Invalid clientId passed: ${clientId}`);
    }

    const url = `https://lyvframe.com/nba/peek_shot?client_id=${clientId}`;
    console.log("URL:", url);

    const response = await fetch(url);

    if (!response.ok) {
      throw new Error(`Bad response (${response.status})`);
    }

    if (response.status === 204) return null;

    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching new shot log:", error);
    return null;
  }
};
