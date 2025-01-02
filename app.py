'''
Radiomics extraction utility User Interface

Pavel Figueroa 

figueroa.pav@gmail.com

This project is a part of a set of utilities in the radiomics workflow analysis with pyradiomics

This utility is used to extract radiomics features from a list of volumes and segmentations, 
it saves directly to a mongodb database as an option, and it saves the result in a json file
it helps to automate the extraction task

'''


from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QGridLayout, QLineEdit, QFileDialog, QMessageBox, QCheckBox, QProgressBar, QTableWidget, QTableWidgetItem, QMainWindow, QTextBrowser
from PyQt6.QtCore import Qt, QSize, QRect, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QWindow
from PyQt6 import QtWidgets

import sys
import os
import time
import json
import csv
import threading

import pymongo
import numpy
import radiomics


def extractRadiomics(File_volume, File_mask, rdm_params):
    try:
        print(f'[1] Loading radiomics ...')
        rmics = radiomics.featureextractor.RadiomicsFeatureExtractor()
        print(f'[2] Loading files ...')
        rmics.loadImage(str(File_volume), str(File_mask))
        print(f'[3] Enable features ...')
        rmics.enableAllFeatures()
        rmics.loadJSONParams(  json.dumps(rdm_params)  )
        print(f'[4] Radiomics extraction ...')
        result = rmics.execute(File_volume, File_mask)
        print(f'[5]Radiomics features calculated')
        return True, result
    except Exception as e:
        print(f"[Error] {e}")
        return False, None


def formatResult( result, id_ ):
    predoc = dict()
    predoc['_ID_'] = str(id_)
    print(f"Formating radiomics result...")
    try:
        for _key_ in result.keys().__iter__():
            if( type(result[str(_key_)]) == str ):
                predoc[str(_key_)] = str(result[str(_key_)])
            elif( type(result[str(_key_)]) == dict ):
                predoc[str(_key_)] = result[str(_key_)]
            elif( type(result[str(_key_)]) == tuple ):
                predoc[str(_key_)] = str(result[str(_key_)])
            if( type(result[str(_key_)]) == numpy.float64 ):
                predoc[str(_key_)] = float(result[str(_key_)])
            elif( type(result[str(_key_)]) == numpy.ndarray ):
                pre = result[str(_key_)].tolist()
                predoc[str(_key_)] = float(pre)

        return True, predoc
    except Exception as e:
        print(f"[Error] While triying to format radiomics result: {e}")
        return False, predoc


class jsonviewer(QWidget):
    def __init__(self, parent):
        QWidget.__init__(self)

        self.setWindowTitle("Json viewer")
        self.setGeometry(200, 200, 800, 600)

        self.text_browser = QTextBrowser(minimumWidth=800, minimumHeight=600)
        self.text_browser.setAcceptRichText(True)

        self.grid = QGridLayout()
        self.grid.addWidget(self.text_browser, 0, 0, 1, 3)
        self.setLayout(self.grid)


    def setDocument(self, document):
        doc = "<style> .tab2 {tab-size: 4;} </style>"
        doc += "{<br>"

        for items in document:
            doc += "<b class=\"tab2\">" +items + ":</b>"
            doc += json.dumps(document[items])
            doc += "<br>"

        doc += "}"
        self.text_browser.setHtml(doc)

# --------------------------------- Radiomics Progress ---------------------------------

class radiomicsProgress(QWidget):
    finish = pyqtSignal()
    def __init__(self):
        QWidget.__init__(self)
        self.setWindowTitle("Radiomics Progress")
        self.setAutoFillBackground(True)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self.setGeometry(200, 200, 800, 600)

        self.label_0 = QLabel('', self)
        self.label_0.move(10, 20)
        self.label_0.resize(700,28)

        self.label_1 = QLabel('', self)
        self.label_1.move(10, 40)
        self.label_1.resize(700,28)

        self.label_2 = QLabel('', self)
        self.label_2.move(10, 60)
        self.label_2.resize(700,28)

        self.label_3 = QLabel('', self)
        self.label_3.move(10, 80)
        self.label_3.resize(700,28)

        self.progressBar = QProgressBar(self)
        self.progressBar.move(10,120)
        self.progressBar.resize(700,28)

        self.usingDatabase = False
        self.databaseConnectionString = f""
        self.database = f""
        self.collection = f""
        self.client = None

    def setUsingDatabase(self, usingdb):
        if type(usingdb) is bool:
            self.usingDatabase = usingdb
        else:
            raise TypeError("Argument should be a boolean") 

    def setDatabaseconnection(self, connstr, database, collection):
        self.databaseConnectionString = connstr
        self.database = database
        self.collection = collection

    def setWorkingList(self, worklist):
        self.worklist = worklist

    def setRadiomicsParams(self, params):
        # Add check params format
        self.radiomicsParams = params

    def exec(self):
        thr = threading.Thread(target=self.__exec__, daemon=True)
        thr.start()

    def __exec__(self):
        items = len(self.worklist)
        item = 0
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(items)

        if self.usingDatabase:
            try:
                self.client = pymongo.MongoClient(self.databaseConnectionString)
            except Exception as e:
                print(f"[Error] while connect to the database: {e}")
                self.client = None

        for volumes in self.worklist:
            filesExistCheck = os.path.exists(volumes[1]) and os.path.exists(volumes[2])
            item += 1

            if filesExistCheck:
                print(f"Processing ...")
                print(f"ID:  {volumes[0]}")
                print(f"Volume:    {volumes[1]}")
                print(f"Segment:   {volumes[2]}")
                self.label_0.setText(f"Processing ...")
                self.label_1.setText(f"Process for ID:  {volumes[0]}")
                self.label_2.setText(f"Volume:    {volumes[1]}")
                self.label_3.setText(f"Segment:   {volumes[2]}")

                isDone, result = extractRadiomics(volumes[1], volumes[2], self.radiomicsParams)

                if isDone:
                    formatDone, dradiomics_document = formatResult( result, volumes[0])
                    if formatDone:
                        try:
                            with open(f'{volumes[0]}.json', 'w') as fp:
                                json.dump(dradiomics_document, fp)
                        except Exception as e:
                            print(f"[Error] while trying to save radiomics result in the file {volumes[0]}.json: {e}")
                    
                    if self.usingDatabase:
                        try:
                            self.client[self.database][self.collection].insert_one(dict(dradiomics_document))
                        except Exception as e:
                            print(f"[Error] while trying to save radiomics result in the database {volumes[0]}: {e}")
                
            else:
                print(f"[Error] No such file:")
                print(f"ID:  {volumes[0]}")
                print(f"Volume:    {volumes[1]}")
                print(f"Segment:   {volumes[2]}")
                self.label_0.setText(f"[Error] No such file:")
                self.label_1.setText(f"Process for ID:  {volumes[0]}")
                self.label_2.setText(f"Volume:    {volumes[1]}")
                self.label_3.setText(f"Segment:   {volumes[2]}")
            
            self.progressBar.setValue(item)

        if self.usingDatabase:
            try:
                self.client.close()
            except:
                pass
            self.client = None
        self.finish.emit()            

# ------------------------------- End Radiomics Progress -------------------------------
        

class RdmWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.error = False
        self.mssg = f""
        self.cont = False

        self.InitialID = f""
        self.InitialVolumeFile = f""
        self.InitialSegmentFile = f""

        self.fileList=[]

        self.OuputDirectory = f""
        self.UseDB = False
        self.DBConnection = False

        self.DatabaseConnectionString = f""
        self.DatabaseName = f""
        self.DatabaseCollection = f""

        self.jsonviewerWidget = jsonviewer(self)
        self.jsonparamsfile = json.loads(r'{"setting": {"binWidth": 25.0, "symmetricalGLCM": true}, "featureClass": {"firstorder": null, "glcm": null, "gldm": null, "glrlm": null, "glszm": null, "ngtdm": null, "shape": null, "shape2D": null}, "imageType": {"Original": {} }}')
        self.progress = radiomicsProgress()
        self.progress.finish.connect(self.radiomicsExtractionFinish)

    def initUI(self):
        self.setWindowTitle('Radiomics GUI utility')
        self.setGeometry(100, 100, 810, 810)

        layout = QGridLayout()
        self.setStyleSheet('font-size: 13px')

        self.label_1 = QLabel('ID:', self)
        layout.addWidget(self.label_1, 0, 1)
        self.label_1.move(5, 10)
        self.line_edit_1_ID = QLineEdit(self)
        layout.addWidget(self.line_edit_1_ID, 1, 1)
        self.line_edit_1_ID.move(140, 10)

        #------------------ Radiomics parameters secction ------------------------------------

        self.button_AddRadiomicsButton = QPushButton('Add Radiomics File', self)
        self.button_AddRadiomicsButton.move(500, 10)
        self.button_AddRadiomicsButton.resize(140, 28)
        self.button_AddRadiomicsButton.clicked.connect(self.on_button_click_AddRadiomicsButton)

        self.button_ViewRadiomicsButton = QPushButton('View', self)
        self.button_ViewRadiomicsButton.move(700, 10)
        self.button_ViewRadiomicsButton.clicked.connect(self.on_button_click_ViewRadiomicsButton)


        #------------------ Radiomics Volumes section     ------------------------------------

        self.label_2 = QLabel('Volume file:', self)
        layout.addWidget(self.label_2, 0, 2)
        self.label_2.move(5, 40)
        self.line_edit_2_VolumeFile = QLineEdit(self)
        layout.addWidget(self.line_edit_2_VolumeFile, 1, 2)
        self.line_edit_2_VolumeFile.move(140, 40)
        self.line_edit_2_VolumeFile.resize(300, 28)
        self.button_AddVolumeFile = QPushButton('Add Volume File', self)
        layout.addWidget(self.button_AddVolumeFile, 2, 4)
        self.button_AddVolumeFile.move(500, 40)
        self.button_AddVolumeFile.resize(140, 28)
        self.button_AddVolumeFile.clicked.connect(self.on_button_click_add_volume_file)

        self.label_3 = QLabel('Segment file:', self)
        layout.addWidget(self.label_3, 0, 3)
        self.label_3.move(5, 70)
        self.line_edit_3_SegmentFile = QLineEdit(self)
        layout.addWidget(self.line_edit_3_SegmentFile, 1, 3)
        self.line_edit_3_SegmentFile.move(140, 70)
        self.line_edit_3_SegmentFile.resize(300, 28)
        self.button_AddSegmentFile = QPushButton('Add Segment File', self)
        layout.addWidget(self.button_AddSegmentFile, 3, 3)
        self.button_AddSegmentFile.move(500, 70)
        self.button_AddSegmentFile.resize(140, 28)
        self.button_AddSegmentFile.clicked.connect(self.on_button_click_add_segment_file)

        self.button_Add = QPushButton('Add to list', self)
        layout.addWidget(self.button_Add, 3, 4)
        self.button_Add.move(500, 110)
        self.button_Add.clicked.connect(self.on_button_click_add)

        self.button_Clear = QPushButton('Clear', self)
        self.button_Clear.move(700, 110)
        self.button_Clear.clicked.connect(self.on_button_click_clear)

        # ---------------------------------------------------------------------------

        self.label_4 = QLabel('Output directory:', self)
        self.label_4.move(5, 150)
        self.line_edit_4_OutputDirectory = QLineEdit(self)
        self.line_edit_4_OutputDirectory.move(140, 150)
        self.line_edit_4_OutputDirectory.resize(300, 28)

        self.button_OutputDirectory = QPushButton('Add Output Directory', self)
        self.button_OutputDirectory.move(500, 150)
        self.button_OutputDirectory.resize(140, 28)
        self.button_OutputDirectory.clicked.connect(self.on_button_click_OutputDirectory)
        

        self.label_5 = QLabel('Database Str:', self)
        self.label_5.move(5, 180)
        self.line_edit_5_DatabaseHost = QLineEdit(self)
        self.line_edit_5_DatabaseHost.move(140, 180)
        self.line_edit_5_DatabaseHost.resize(300, 28)

        
        self.checkBox_useDataBase = QCheckBox(self)
        self.checkBox_useDataBase.move(500,180)
        self.label_7 = QLabel('Use database', self)
        self.label_7.move(520,180)

        self.label_8 = QLabel('Database:', self)
        self.label_8.move(5, 210)
        self.line_edit_8_Database = QLineEdit(self)
        self.line_edit_8_Database.move(140, 210)
        self.line_edit_8_Database.resize(200, 28)

        self.label_9 = QLabel('Collection:', self)
        self.label_9.move(5, 240)
        self.line_edit_9_Collection = QLineEdit(self)
        self.line_edit_9_Collection.move(140, 240)
        self.line_edit_9_Collection.resize(200, 28)

        self.button_test = QPushButton('Test Connection', self)
        self.button_test.move(500, 300)
        self.button_test.clicked.connect(self.on_button_click_DBConnectionTest)

        self.button_exec = QPushButton('Exec', self)
        self.button_exec.move(700, 300)
        self.button_exec.clicked.connect(self.on_button_click_exec)

        self.table = QTableWidget(self)
        self.table.setGeometry(0, 0, 790, 350)
        self.table.move(5,400)
        self.table.setColumnCount(3)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 370)
        self.table.setColumnWidth(2, 370)
        self.table.setHorizontalHeaderLabels(["ID","Volume", "Segment"])
        self.table.horizontalHeader().setVisible(True)

        self.button_DeletSelected = QPushButton('Delet selected', self)
        layout.addWidget(self.button_DeletSelected, 2, 4)
        self.button_DeletSelected.move(500, 760)
        self.button_DeletSelected.clicked.connect(self.on_button_click_DeletSelected)

        self.button_ImportList = QPushButton('Import List', self)
        layout.addWidget(self.button_ImportList, 2, 4)
        self.button_ImportList.move(10, 760)
        self.button_ImportList.clicked.connect(self.on_button_click_ImportList)


        self.show()

    # ----------------------------- end of -----------------------------------

    def on_button_click_AddRadiomicsButton(self):
        self.mssg = ""
        self.error = False
        jsonparamsfile, _ = QFileDialog.getOpenFileName(self,"Choose Radiomics parameters File", "","JavaScript Object Notation Files (*.json);;All Files (*)")
        try:
            with open(jsonparamsfile, 'r') as file:
                self.jsonparamsfile = json.load(file)
        except:
            self.mssg = "File can not be readed, pelase cheack if it is a valid json format"
            self.error = True

        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)

    def on_button_click_ViewRadiomicsButton(self):
        self.mssg = ""
        self.error = False
        self.jsonviewerWidget.setDocument(self.jsonparamsfile)
        self.jsonviewerWidget.show()


        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)

    def on_button_click_add_volume_file(self):
        self.InitialVolumeFile, _ = QFileDialog.getOpenFileName(self,"Choose Volume File", "","Nearly Raw Raster Data Files (*.nrrd);;All Files (*)")
        self.line_edit_2_VolumeFile.setText(self.InitialVolumeFile)

    def on_button_click_add_segment_file(self):
        self.InitialSegmentFile, _ = QFileDialog.getOpenFileName(self,"Choose Volume File", "","Nearly Raw Raster Data Files (*.nrrd);;All Files (*)")
        self.line_edit_3_SegmentFile.setText(self.InitialSegmentFile)

    def on_button_click_clear(self):
        self.InitialID = ""
        self.InitialVolumeFile = ""
        self.InitialSegmentFile = ""

        self.line_edit_1_ID.setText(self.InitialID)
        self.line_edit_2_VolumeFile.setText(self.InitialVolumeFile)
        self.line_edit_3_SegmentFile.setText(self.InitialSegmentFile)

    def on_button_click_add(self):
        self.mssg = ""
        self.error = False


        self.InitialID = self.line_edit_1_ID.text()
        self.InitialVolumeFile = self.line_edit_2_VolumeFile.text()
        self.InitialSegmentFile = self.line_edit_3_SegmentFile.text()

        lenCheck = (len(self.InitialID) > 0) and (len(self.InitialVolumeFile) > 0) and (len(self.InitialSegmentFile) > 0)
        filesExistCheck = os.path.exists(self.InitialVolumeFile) and os.path.exists(self.InitialSegmentFile)

        if lenCheck:
            if filesExistCheck:
                self.fileList.append([self.InitialID, self.InitialVolumeFile, self.InitialSegmentFile])
                self.table.setRowCount( len(self.fileList) )
                row = 0
                for rows in self.fileList:
                    self.table.setItem(row, 0, QTableWidgetItem( rows[0] ))
                    self.table.setItem(row, 1, QTableWidgetItem( rows[1] ))
                    self.table.setItem(row, 2, QTableWidgetItem( rows[2] ))
                    row += 1
            else:
                print(f"One or more files do not exist")
                self.error = True
                self.mssg = f"One or more files do not exist"
        else:
            print(f"One or more fields are empty")
            self.error = True
            self.mssg = f"One or more fields are empty"
        
        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)
    
    def on_button_click_OutputDirectory(self):
        self.OuputDirectory = QFileDialog.getExistingDirectory(self, "Select Directory")
        self.line_edit_4_OutputDirectory.setText(self.OuputDirectory)
    
    def on_button_click_DBConnectionTest(self):
        setDatabaseParams = self. __setDatabaseParams__()

        if setDatabaseParams and self.DBConnection:
            QMessageBox.information(self, "Information", "Database test connection successful!")

    def __setDatabaseParams__(self):
        self.error = False
        self.mssg = f""

        self.DatabaseConnectionString = self.line_edit_5_DatabaseHost.text()
        self.DatabaseName = self.line_edit_8_Database.text()
        self.DatabaseCollection = self.line_edit_9_Collection.text()

        lenCheck = ( len(self.DatabaseConnectionString) > 0) and (len(self.DatabaseName) > 0) and (len(self.DatabaseCollection) > 0)

        if not lenCheck:
            self.error = True
            self.mssg = f"One or more database fields are empty"
        else:
            #------------------------- Database Connection ------------------------
            try:
                client = pymongo.MongoClient(self.DatabaseConnectionString)
                if ( self.DatabaseName in client.list_database_names() ):
                    if ( self.DatabaseCollection in client[self.DatabaseName].list_collection_names() ):
                        self.DBConnection = True
                    else:
                        self.error = True
                        self.mssg = f"collection does not exist: {client[self.DatabaseName].list_collection_names()}"
                        self.DBConnection = False
                else:
                    self.error = True
                    self.mssg = f"Database does not exist: {client.list_database_names()}"
                    self.DBConnection = False
                client.close()
            except Exception as e:
                self.error = True
                self.mssg = f"{e}"
                self.DBConnection = False



        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)
        
        return not self.error
    
    def on_button_click_exec(self):
        self.error = False
        self.mssg = f""
        self.cont = False

        if len(self.fileList) < 1:
            self.mssg = f"working list is empty"
            self.error = True
        else:
            if os.path.exists(self.OuputDirectory):

                if self.checkBox_useDataBase.isChecked():
                    self.__setDatabaseParams__()
                    if self.DBConnection:
                        # --------------------------    Radiomics extraction using database --------------------------
                        os.chdir(self.OuputDirectory)
                        rows = len(self.fileList)
                        self.setEnabled(False)
                        self.progress.show()
                        self.progress.setUsingDatabase(True)
                        self.progress.setDatabaseconnection(self.DatabaseConnectionString, self.DatabaseName, self.DatabaseCollection)
                        self.progress.setWorkingList(self.fileList)
                        self.progress.setRadiomicsParams(self.jsonparamsfile)
                        self.progress.exec()
                        # --------------------------  End Radiomics extraction using database --------------------------
                    else:
                        self.error = True
                        self.mssg = "Database connection error!"
                else:
                    # --------------------------    Radiomics extraction   --------------------------
                    os.chdir(self.OuputDirectory)
                    rows = len(self.fileList)
                    self.setEnabled(False)
                    self.progress.show()
                    self.progress.setUsingDatabase(False)
                    self.progress.setWorkingList(self.fileList)
                    self.progress.setRadiomicsParams(self.jsonparamsfile)
                    self.progress.exec()
                    # --------------------------  End Radiomics extraction --------------------------

            else:
                self.error = True
                self.mssg = "Output directory does not exist"
        
        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)
            self.setEnabled(True)

    def radiomicsExtractionFinish(self):
        QMessageBox.information(self, "Information", "Radiomics work is done.")
        self.progress.close()
        self.setEnabled(True)

    
    def on_button_click_DeletSelected(self):
        self.error = False
        self.mssg = f""

        row = self.table.currentRow()

        if row < 0:
            self.error = True
            self.mssg = f"No row selected"
        else:
            del self.fileList[row]
            self.table.setRowCount( len(self.fileList) )
            row = 0
            for rows in self.fileList:
                self.table.setItem(row, 0, QTableWidgetItem( rows[0] ))
                self.table.setItem(row, 1, QTableWidgetItem( rows[1] ))
                self.table.setItem(row, 2, QTableWidgetItem( rows[2] ))
                row += 1

        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)

    def on_button_click_ImportList(self):
        self.error = False
        self.mssg = f""
        listFile, _ = QFileDialog.getOpenFileName(self,"Choose list File", "","Comma Ceparated Values Files (*.csv);;All Files (*)")

        if os.path.exists(listFile):
            try:
                self.fileList = []
                with open(listFile) as fobj:
                    csvreader = csv.reader(fobj)
                    for rr in csvreader:
                        self.fileList.append(rr)
                
                self.table.setRowCount( len(self.fileList) )
                row = 0
                for rows in self.fileList:
                    self.table.setItem(row, 0, QTableWidgetItem( rows[0] ))
                    self.table.setItem(row, 1, QTableWidgetItem( rows[1] ))
                    self.table.setItem(row, 2, QTableWidgetItem( rows[2] ))
                    row += 1
            except:
                self.error = True
                self.mssg = f"Error While trying to open file {listFile}"
                self.fileList = []
                self.table.setRowCount( len(self.fileList) )
                

        if self.error:
            QMessageBox.critical(self, "Error", self.mssg)



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RdmWindow()
    sys.exit(app.exec())