// utils/storage.js
import AsyncStorage from '@react-native-async-storage/async-storage';
import 'react-native-get-random-values';
import { v4 as uuidv4 } from 'uuid';

const CLIENT_ID_KEY = 'client_id';

export const getClientId = async () => {
  try {
    let clientId = await AsyncStorage.getItem(CLIENT_ID_KEY);
    if (!clientId) {
      clientId = uuidv4();
      await AsyncStorage.setItem(CLIENT_ID_KEY, clientId);
    }
    return clientId;
  } catch (e) {
    console.error('Failed to load/set client ID:', e);
    throw e;
  }
};
