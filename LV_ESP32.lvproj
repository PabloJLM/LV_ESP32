<?xml version='1.0' encoding='UTF-8'?>
<Project Type="Project" LVVersion="25008000">
	<Property Name="NI.LV.All.SaveVersion" Type="Str">25.0</Property>
	<Property Name="NI.LV.All.SourceOnly" Type="Bool">true</Property>
	<Item Name="My Computer" Type="My Computer">
		<Property Name="NI.SortType" Type="Int">3</Property>
		<Property Name="server.app.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.control.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.tcp.enabled" Type="Bool">false</Property>
		<Property Name="server.tcp.port" Type="Int">0</Property>
		<Property Name="server.tcp.serviceName" Type="Str">My Computer/VI Server</Property>
		<Property Name="server.tcp.serviceName.default" Type="Str">My Computer/VI Server</Property>
		<Property Name="server.vi.callsEnabled" Type="Bool">true</Property>
		<Property Name="server.vi.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="specify.custom.address" Type="Bool">false</Property>
		<Item Name="config" Type="Folder">
			<Item Name="Detector_COM.vi" Type="VI" URL="../Detector_COM.vi"/>
			<Item Name="Config_Wifi.vi" Type="VI" URL="../Config_Wifi.vi"/>
			<Item Name="Compile.vi" Type="VI" URL="../Compile.vi"/>
			<Item Name="Firmware.vi" Type="VI" URL="../Firmware.vi"/>
			<Item Name="test_firmware.vi" Type="VI" URL="../test_firmware.vi"/>
			<Item Name="Upload.vi" Type="VI" URL="../Upload.vi"/>
		</Item>
		<Item Name="Ejemplos" Type="Folder">
			<Item Name="PRUEBAS.vi" Type="VI" URL="../PRUEBAS.vi"/>
			<Item Name="Tets.vi" Type="VI" URL="../Tets.vi"/>
			<Item Name="Prueba_report.vi" Type="VI" URL="../Prueba_report.vi"/>
			<Item Name="PRUEBA_ANALOG.vi" Type="VI" URL="../PRUEBA_ANALOG.vi"/>
			<Item Name="Prueba_mqtt.vi" Type="VI" URL="../Prueba_mqtt.vi"/>
			<Item Name="prueba_dac.vi" Type="VI" URL="../prueba_dac.vi"/>
			<Item Name="PRUEBA_NEO_I.vi" Type="VI" URL="../PRUEBA_NEO_I.vi"/>
			<Item Name="PRUEBA_NEO.vi" Type="VI" URL="../PRUEBA_NEO.vi"/>
			<Item Name="PRUEBA_DIG.vi" Type="VI" URL="../PRUEBA_DIG.vi"/>
			<Item Name="PRUEBA_A_IO.vi" Type="VI" URL="../PRUEBA_A_IO.vi"/>
			<Item Name="Generador de funciones.vi" Type="VI" URL="../Generador de funciones.vi"/>
		</Item>
		<Item Name="Funciones_basicas" Type="Folder">
			<Item Name="Close_ESP.vi" Type="VI" URL="../Close_ESP.vi"/>
			<Item Name="Open_ESP.vi" Type="VI" URL="../Open_ESP.vi"/>
			<Item Name="Digital_Write.vi" Type="VI" URL="../Digital_Write.vi"/>
			<Item Name="Digital_Read.vi" Type="VI" URL="../Digital_Read.vi"/>
			<Item Name="analog_read.vi" Type="VI" URL="../analog_read.vi"/>
			<Item Name="DAC.vi" Type="VI" URL="../DAC.vi"/>
			<Item Name="PWM_Write.vi" Type="VI" URL="../PWM_Write.vi"/>
		</Item>
		<Item Name="Funciones_especiales" Type="Folder">
			<Item Name="NP_Control.vi" Type="VI" URL="../NP_Control.vi"/>
			<Item Name="NPI_Control.vi" Type="VI" URL="../NPI_Control.vi"/>
			<Item Name="MQTT_PUBLISH.vi" Type="VI" URL="../MQTT_PUBLISH.vi"/>
			<Item Name="MQTT_SUBS.vi" Type="VI" URL="../MQTT_SUBS.vi"/>
			<Item Name="MQTT_CLOSE.vi" Type="VI" URL="../MQTT_CLOSE.vi"/>
			<Item Name="report_view.vi" Type="VI" URL="../report_view.vi"/>
			<Item Name="report_gen.vi" Type="VI" URL="../report_gen.vi"/>
			<Item Name="Acelerometro.vi" Type="VI" URL="../Acelerometro.vi"/>
		</Item>
		<Item Name="Funciones_AUX" Type="Folder">
			<Item Name="Signal_Gen.vi" Type="VI" URL="../Signal_Gen.vi"/>
			<Item Name="3D_boc.vi" Type="VI" URL="../3D_boc.vi"/>
		</Item>
		<Item Name="LV_ESP32.lvlib" Type="Library" URL="../LV_ESP32.lvlib"/>
		<Item Name="Prueba_acelerometro.vi" Type="VI" URL="../Prueba_acelerometro.vi"/>
		<Item Name="Prueba_PWM.vi" Type="VI" URL="../Prueba_PWM.vi"/>
		<Item Name="PRUEBA_A_PWM.vi" Type="VI" URL="../PRUEBA_A_PWM.vi"/>
		<Item Name="Dependencies" Type="Dependencies"/>
		<Item Name="Build Specifications" Type="Build">
			<Item Name="LV_ESP32" Type="Packed Library">
				<Property Name="Bld_autoIncrement" Type="Bool">true</Property>
				<Property Name="Bld_buildCacheID" Type="Str">{EAEF433A-9FE1-48ED-9C32-FBC1773416BE}</Property>
				<Property Name="Bld_buildSpecName" Type="Str">LV_ESP32</Property>
				<Property Name="Bld_excludeLibraryItems" Type="Bool">true</Property>
				<Property Name="Bld_excludePolymorphicVIs" Type="Bool">true</Property>
				<Property Name="Bld_localDestDir" Type="Path">../builds/NI_AB_PROJECTNAME/LV_ESP32</Property>
				<Property Name="Bld_localDestDirType" Type="Str">relativeToCommon</Property>
				<Property Name="Bld_modifyLibraryFile" Type="Bool">true</Property>
				<Property Name="Bld_previewCacheID" Type="Str">{20CFA195-5C06-4362-BD40-A83B2756939C}</Property>
				<Property Name="Bld_version.build" Type="Int">12</Property>
				<Property Name="Bld_version.major" Type="Int">1</Property>
				<Property Name="Destination[0].destName" Type="Str">LV_ESP32.lvlibp</Property>
				<Property Name="Destination[0].path" Type="Path">../builds/NI_AB_PROJECTNAME/LV_ESP32/LV_ESP32.lvlibp</Property>
				<Property Name="Destination[0].preserveHierarchy" Type="Bool">true</Property>
				<Property Name="Destination[0].type" Type="Str">App</Property>
				<Property Name="Destination[1].destName" Type="Str">Support Directory</Property>
				<Property Name="Destination[1].path" Type="Path">../builds/NI_AB_PROJECTNAME/LV_ESP32</Property>
				<Property Name="DestinationCount" Type="Int">2</Property>
				<Property Name="PackedLib_callersAdapt" Type="Bool">true</Property>
				<Property Name="Source[0].itemID" Type="Str">{C9033DDE-1FE7-411C-97B4-3CAD542577FE}</Property>
				<Property Name="Source[0].type" Type="Str">Container</Property>
				<Property Name="Source[1].destinationIndex" Type="Int">0</Property>
				<Property Name="Source[1].itemID" Type="Ref">/My Computer/LV_ESP32.lvlib</Property>
				<Property Name="Source[1].Library.allowMissingMembers" Type="Bool">true</Property>
				<Property Name="Source[1].Library.atomicCopy" Type="Bool">true</Property>
				<Property Name="Source[1].Library.LVLIBPtopLevel" Type="Bool">true</Property>
				<Property Name="Source[1].preventRename" Type="Bool">true</Property>
				<Property Name="Source[1].sourceInclusion" Type="Str">TopLevel</Property>
				<Property Name="Source[1].type" Type="Str">Library</Property>
				<Property Name="SourceCount" Type="Int">2</Property>
				<Property Name="TgtF_companyName" Type="Str">Universidad Galileo</Property>
				<Property Name="TgtF_enableDebugging" Type="Bool">true</Property>
				<Property Name="TgtF_fileDescription" Type="Str">LV_ESP32</Property>
				<Property Name="TgtF_internalName" Type="Str">LV_ESP32</Property>
				<Property Name="TgtF_legalCopyright" Type="Str">Copyright © 2025 Universidad Galileo</Property>
				<Property Name="TgtF_productName" Type="Str">LV_ESP32</Property>
				<Property Name="TgtF_targetfileGUID" Type="Str">{D1F8CC6C-B4C6-411E-9BEC-25444D1B4328}</Property>
				<Property Name="TgtF_targetfileName" Type="Str">LV_ESP32.lvlibp</Property>
				<Property Name="TgtF_versionIndependent" Type="Bool">true</Property>
			</Item>
		</Item>
	</Item>
</Project>
