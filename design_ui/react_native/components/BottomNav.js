import React from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { colors } from '../styles';

const tabs = ['Parameters','Metrics','Standards'];

export default function BottomNav({active, onChange}){
  return (
    <View style={styles.container}>
      {tabs.map(t => (
        <TouchableOpacity key={t} style={styles.button} onPress={()=>onChange(t)}>
          <View style={styles.iconPlaceholder} />
          <Text style={[styles.label, active===t && styles.active]}>{t}</Text>
        </TouchableOpacity>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    height: 88,
    flexDirection: 'row',
    backgroundColor: 'rgba(255,255,255,0.02)',
    justifyContent: 'space-around',
    alignItems: 'center',
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.03)'
  },
  button: { alignItems: 'center' },
  iconPlaceholder: { width:28, height:28, borderRadius:6, backgroundColor:'rgba(255,255,255,0.03)' },
  label: { color: colors.secondary, fontSize:12, marginTop:6 },
  active: { color: colors.cyan, textShadowColor: colors.cyan, textShadowOffset: {width:0, height:0}, textShadowRadius:8 }
});
