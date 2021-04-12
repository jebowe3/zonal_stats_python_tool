import os
import tkinter as tk
from tkinter.filedialog import askdirectory
from tkinter.filedialog import askopenfilename
import tkinter.messagebox
from osgeo import gdal
from osgeo import ogr, osr
import numpy as np
from numpy import zeros
from numpy import logical_and
import rasterio as rio
from rasterstats import zonal_stats

print("Modules imported!\n-----")
print("Initializing code...")

##  Set up class frame
class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.grid()

        ##  Commands

        ##  G-1. Return Shapefile Path
        def BrowseFile_1():
            var_1.set(askopenfilename(title="Select the shapefile for your area of interest"))

        ##  G-2. Return Raster File Path
        def BrowseFile_2():
            var_2.set(askopenfilename(title="Select the raster for zonal analysis"))

        ## G-3. Return Lowest Value of Desired Raster Class
        def BrowseLabel_3():
            var_3.set(askinteger(title="Input the lowest value in the raster classification range you want to analyze"))

        ## G-4. Return Highest Value of Desired Raster Class
        def BrowseLabel_4():
            var_4.set(askinteger(title="Input the highest value in the raster classification range you want to analyze"))

        ##  G-5. Run the Script
        def OK():       
            
            ##  Define input variables
            input_zone_polygon = var_1.get()
            input_value_raster = var_2.get()
            low_class_str = var_3.get()
            high_class_str = var_4.get()

            ## Convert numeric strings to integers
            low_class_int = int(low_class_str)
            high_class_int = int(high_class_str)

            ## Ensure all entries are filled
            if input_zone_polygon == "":
                print("Error: Select the shapefile for your area of interest")
            if input_value_raster == "":
                print("Error: Select the raster for zonal analysis")
            if low_class_int == "":
                print("Error: Input the lowest value in the raster classification range you want to analyze")
            if high_class_int == "":
                print("Error: Input the highest value in the raster classification range you want to analyze")
            
            print('Retrieving the directory path for the input raster.')

            ## Get the directory path of the input raster
            ras_dir_path = os.path.dirname(input_value_raster)

            print('Retrieving the file extension of the input raster.')

            ## Get the file extension of the raster file
            file_ext = os.path.splitext(input_value_raster)[1]

            print('Checking if the file extension of the input raster is tif or img.')

            if file_ext == '.tif':
                drive = 'GTiff'
            elif file_ext == '.img':
                drive = 'HFA'
            else:
                print('Error: The input raster file needs to be in .tif or .img format.')
                
            print('Reclassifying the raster to a binary 0,1 classification...')
            
            #Define the gdal driver with the drive variable from the conditional test
            driver = gdal.GetDriverByName(drive)

            file = gdal.Open(input_value_raster)
            band = file.GetRasterBand(1)
            
            # reclassification
            classification_values = [0,low_class_int,high_class_int + 1]
            classification_output_values = [0,1,0]

            block_sizes = band.GetBlockSize()
            x_block_size = block_sizes[0]
            y_block_size = block_sizes[1]

            xsize = band.XSize
            ysize = band.YSize

            max_value = band.GetMaximum()
            min_value = band.GetMinimum()

            if max_value == None or min_value == None:
                stats = band.GetStatistics(0, 1)
                max_value = stats[1]
                min_value = stats[0]

            # create new file
            file2 = driver.Create( ras_dir_path + '/raster2' + file_ext, xsize , ysize , 1, gdal.GDT_Byte)

            # spatial ref system
            file2.SetGeoTransform(file.GetGeoTransform())
            file2.SetProjection(file.GetProjection())

            print('Reassigning raster values...please wait...')
            for i in range(0, ysize, y_block_size):
                if i + y_block_size < ysize:
                    rows = y_block_size
                else:
                    rows = ysize - i
                for j in range(0, xsize, x_block_size):
                    if j + x_block_size < xsize:
                        cols = x_block_size
                    else:
                        cols = xsize - j

                    data = band.ReadAsArray(j, i, cols, rows)
                    r = zeros((rows, cols), np.uint8)

                    for k in range(len(classification_values) - 1):
                        if classification_values[k] <= max_value and (classification_values[k + 1] > min_value ):
                            r = r + classification_output_values[k] * logical_and(data >= classification_values[k], data < classification_values[k + 1])
                    if classification_values[k + 1] < max_value:
                        r = r + classification_output_values[k+1] * (data >= classification_values[k + 1])

                    file2.GetRasterBand(1).WriteArray(r,j,i)

            file2 = None

            print('Done reclassifying the raster. Reprojecting the raster to the shapefile projection...')
            print('Identifying the EPSG code of the input SHP')
            
            # Get the EPSG code of the input shapefile
            shp_driver = ogr.GetDriverByName('ESRI Shapefile')
            dataset = shp_driver.Open(input_zone_polygon)
            layer = dataset.GetLayer()
            spatialRef = layer.GetSpatialRef()
            shp_epsg = spatialRef.GetAttrValue("GEOGCS|AUTHORITY", 1)

            print('Shapefile projection is EPSG:' + shp_epsg + '.')
            print('Reprojecting the raster to match SHP...please wait...')

            # Reproject the raster
            input_raster = gdal.Open(ras_dir_path + '/raster2' + file_ext)
            output_raster = ras_dir_path + '/raster2_reproject' + file_ext

            warp = gdal.Warp(output_raster,input_raster,dstSRS='EPSG:'+str(shp_epsg))
            warp = None

            print('Done reprojecting. Processing zonal statistics...')
            
            zs = zonal_stats(input_zone_polygon,output_raster,stats=['min', 'max', 'mean', 'count', 'sum'])

            print(zs)

            ## Hide the tkinter root box
            root = tk.Tk()
            root.withdraw()

            ## Define each zonal stat
            min = [x['min'] for x in zs]
            max = [x['max'] for x in zs]
            mean = [x['mean'] for x in zs]
            count = [x['count'] for x in zs]
            sum = [x['sum'] for x in zs]

            ## Build the messagebox content
            lines = ["AOI covered by selected raster classes: " + str(round(mean[0]*100,2))+"%", "minimum: " + str(min[0]), "maximum: " + str(max[0]), "count: " + str(count[0]), "sum: " + str(sum[0])]

            ## Display the messagebox content in separate lines
            tk.messagebox.showinfo("Zonal Statistics Summary", "\n".join(lines))

            print('All done processing!')
            
        self.quit()


        ##  GUI Widgets
        ##  G-1. Shapefile Selection
        ##  1-Label
        label_1 = tk.Label(self, text="Select the shapefile for your area of interest")
        label_1.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="W")

        ##  1-Entry Box
        var_1 = tk.StringVar()
        entry_1 = tk.Entry(self, textvariable=var_1)
        entry_1.grid(row=0, column=2, padx=5, pady=5, ipadx=100, sticky="W")

        ##  1-Button
        button_1 = tk.Button(self, text="Browse", command=BrowseFile_1)
        button_1.grid(row=0, column=3, padx=5, pady=5, sticky="E")

        ##  G-2. Raster Selection
        ##  2-Label
        label_2 = tk.Label(self, text="Select the raster for zonal analysis")
        label_2.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="W")

        ##  2-Entry Box
        var_2 = tk.StringVar()
        entry_2 = tk.Entry(self, textvariable=var_2)
        entry_2.grid(row=1, column=2, padx=5, pady=5, ipadx=100, sticky="W")

        ##  2-Button
        button_2 = tk.Button(self, text="Browse", command=BrowseFile_2)
        button_2.grid(row=1, column=3, padx=5, pady=5, sticky="E")

        ##  G-3. Low Class Selection
        ##  3-Label
        label_3 = tk.Label(self, text="Input the lowest value in the raster classification range you want to analyze")
        label_3.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="W")

        ##  3-Entry Box
        var_3 = tk.StringVar()
        entry_3 = tk.Entry(self, textvariable=var_3)
        entry_3.grid(row=2, column=2, padx=5, pady=5, ipadx=100, sticky="W")

        ##  G-4. High Class Selection
        ##  4-Label
        label_4 = tk.Label(self, text="Input the highest value in the raster classification range you want to analyze")
        label_4.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="W")

        ##  4-Entry Box
        var_4 = tk.StringVar()
        entry_4 = tk.Entry(self, textvariable=var_4)
        entry_4.grid(row=3, column=2, padx=5, pady=5, ipadx=100, sticky="W")

        ##  G-5. OK
        ##  5-Button
        button_5 = tk.Button(self, text="OK", command=OK)
        button_5.grid(row=4, column=3, columnspan=2, padx=5, pady=5, ipadx=20, sticky="s")

app = Application()
app.master.title("Zonal Stats Tool")
app.mainloop()
