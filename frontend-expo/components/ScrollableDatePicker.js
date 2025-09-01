import React, { useState, useEffect } from 'react';
import { View } from 'react-native';
import { Picker } from '@react-native-picker/picker';

const YEARS = Array.from({ length: 50 }, (_, i) => 1980 + i);
const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);

const daysInMonth = (year, month) => new Date(year, month, 0).getDate();

export default function ScrollableDatePicker({ onDateChange, initialDate }) {
  const initDate = initialDate || new Date();

  const [year, setYear] = useState(initDate.getFullYear());
  const [month, setMonth] = useState(initDate.getMonth() + 1);
  const [day, setDay] = useState(initDate.getDate());
  const [days, setDays] = useState(daysInMonth(year, month));

  useEffect(() => {
    const dim = daysInMonth(year, month);
    setDays(dim);
    if (day > dim) setDay(dim);
  }, [year, month]);

  useEffect(() => {
    onDateChange && onDateChange(new Date(year, month - 1, day));
  }, [year, month, day]);

  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-around', paddingVertical: 10 }}>
      <Picker
        selectedValue={year}
        style={{ flex: 1 }}
        onValueChange={setYear}
      >
        {YEARS.map((y) => (
          <Picker.Item key={y} label={`${y}`} value={y} />
        ))}
      </Picker>

      <Picker
        selectedValue={month}
        style={{ flex: 1 }}
        onValueChange={setMonth}
      >
        {MONTHS.map((m) => (
          <Picker.Item key={m} label={`${m}`} value={m} />
        ))}
      </Picker>

      <Picker
        selectedValue={day}
        style={{ flex: 1 }}
        onValueChange={setDay}
      >
        {Array.from({ length: days }, (_, i) => i + 1).map((d) => (
          <Picker.Item key={d} label={`${d}`} value={d} />
        ))}
      </Picker>
    </View>
  );
}
