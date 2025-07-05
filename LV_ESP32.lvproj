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
		<Item Name="LV_ESP32.lvlib" Type="Library" URL="../LV_ESP32.lvlib"/>
		<Item Name="Close_ESP.vi" Type="VI" URL="../Close_ESP.vi"/>
		<Item Name="Compile.vi" Type="VI" URL="../Compile.vi"/>
		<Item Name="Config_Wifi.vi" Type="VI" URL="../Config_Wifi.vi"/>
		<Item Name="Detector_COM.vi" Type="VI" URL="../Detector_COM.vi"/>
		<Item Name="Digital_Read.vi" Type="VI" URL="/&lt;vilib&gt;/Prueba/LV_ESP32/Digital_Read.vi"/>
		<Item Name="Digital_Write.vi" Type="VI" URL="../Digital_Write.vi"/>
		<Item Name="Firmware.vi" Type="VI" URL="../Firmware.vi"/>
		<Item Name="MQTT_PUBLISH.vi" Type="VI" URL="../MQTT_PUBLISH.vi"/>
		<Item Name="Open_ESP.vi" Type="VI" URL="../Open_ESP.vi"/>
		<Item Name="pruebas_digr.vi" Type="VI" URL="../../../../../../../Program Files/National Instruments/LabVIEW 2025/examples/Prueba/LV_ESP32/pruebas_digr.vi"/>
		<Item Name="pruebas_digw.vi" Type="VI" URL="../pruebas_digw.vi"/>
		<Item Name="pruebas_mqtt.vi" Type="VI" URL="../pruebas_mqtt.vi"/>
		<Item Name="pruebas_rgb.vi" Type="VI" URL="../pruebas_rgb.vi"/>
		<Item Name="RGB_Control.vi" Type="VI" URL="../RGB_Control.vi"/>
		<Item Name="test_firmware.vi" Type="VI" URL="../test_firmware.vi"/>
		<Item Name="Upload.vi" Type="VI" URL="../Upload.vi"/>
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
				<Property Name="Bld_version.build" Type="Int">8</Property>
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
