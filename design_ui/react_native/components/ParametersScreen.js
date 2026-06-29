import React from 'react';
import { ScrollView, View, Text, TextInput, TouchableOpacity } from 'react-native';
import { styles, colors } from '../styles';

export default function ParametersScreen(){
  return (
    <ScrollView style={{flex:1, backgroundColor: colors.black, padding:18}}>
      <Text style={styles.header}>Parameters</Text>

      {['Plate Marking','Stitching Number','Correction Number','Plate Number','Batch Number'].map((label)=> (
        <View key={label} style={{marginTop:14}}>
          <Text style={styles.label}>{label}</Text>
          <TextInput placeholder={label} placeholderTextColor={'#6b6b6b'} style={styles.input} />
        </View>
      ))}

      <View style={{marginTop:14}}>
        <Text style={styles.label}>Sorting Target</Text>
        <TextInput placeholder="Select target" placeholderTextColor={'#6b6b6b'} style={styles.input} />
      </View>

      <View style={{marginTop:14}}>
        <Text style={styles.label}>Sorting Type</Text>
        <TextInput placeholder="Select type" placeholderTextColor={'#6b6b6b'} style={styles.input} />
      </View>

      <View style={{marginTop:14}}>
        <Text style={styles.label}>Comments</Text>
        <TextInput placeholder="Notes..." placeholderTextColor={'#6b6b6b'} style={[styles.input, {height:140, textAlignVertical:'top'}]} multiline />
      </View>

      <TouchableOpacity style={styles.fab}>
        <Text style={{color:colors.black, fontWeight:'700'}}>Save</Text>
      </TouchableOpacity>

    </ScrollView>
  );
}
