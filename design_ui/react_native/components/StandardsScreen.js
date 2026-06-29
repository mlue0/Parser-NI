import React from 'react';
import { View, Text, ScrollView, TouchableOpacity } from 'react-native';
import { styles, colors } from '../styles';

const standards = [
  ['INL','±0.5','V'],
  ['DNL','±0.3','V'],
  ['U0','1.2','µA'],
  ['UFS','3.3','V'],
  ['Burn','5','s']
];

export default function StandardsScreen(){
  return (
    <ScrollView style={{flex:1, backgroundColor: colors.black, padding:18}}>
      <Text style={styles.header}>Standards</Text>
      <View style={{marginTop:18}}>
        {standards.map(([k,v,u])=> (
          <View key={k} style={{flexDirection:'row', justifyContent:'space-between', alignItems:'center', paddingVertical:14, borderBottomWidth:1, borderBottomColor:'rgba(255,255,255,0.02)'}}>
            <Text style={{color: colors.primary, fontSize:16}}>{k}</Text>
            <View style={{flexDirection:'row', alignItems:'center'}}>
              <Text style={{color: colors.cyan, backgroundColor:'rgba(0,255,240,0.04)', paddingVertical:8, paddingHorizontal:12, borderRadius:12, fontWeight:'700'}}>{v} {u}</Text>
              <TouchableOpacity style={{marginLeft:12}}>
                <Text style={{color:colors.secondary}}>✎</Text>
              </TouchableOpacity>
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}
