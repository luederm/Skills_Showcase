/*
	@author Matthew Lueder
	@date 10/2016
	@description Project 2 - CIS 677
*/
#include <iostream>
#include <fstream>
#include <cstdlib>
#include <string>
#include <vector>
#include <cmath>
#include <ctime>
#include <omp.h>
#include <stdlib.h>
#include <thread>
#include <mutex> 
#include <boost/timer.hpp>

static int THRESHOLD = 70;
static bool ENABLE_MUTEX = false;

#pragma pack(1)
typedef struct {
	char id[2];
	int file_size;
	int reserved;
	int offset;
}  header_type;


#pragma pack(1)
typedef struct {
	int header_size;
	int width;
	int height;
	unsigned short int color_planes;
	unsigned short int color_depth;
	unsigned int compression;
	int image_size;
	int xresolution;
	int yresolution;
	int num_colors;
	int num_important_colors;
} information_type;


typedef struct {
	header_type header;
	information_type info;
	std::vector <std::vector <int> > pixelData;
	int padding;
} Image;


class SharedImage {
	std::mutex m_mutex;
	Image m_image;

public:
	/*
		Construct shared image with a predefined header and info
	*/
	SharedImage(header_type header, information_type info, int padding) {
		m_image.header = header;
		m_image.info = info;
		m_image.padding = padding;
		m_image.pixelData.resize(m_image.info.height);

		for (auto iter = m_image.pixelData.begin(); 
			iter != m_image.pixelData.end(); ++iter)
		{
			iter->resize(m_image.info.width);
		}
	} 

	/*
		Set value of a pixel in the image - threadsafe
	*/
	void setPixel(int x, int y, int value) {
		// MUTEX NOT NEEDED WHEN WRITING TO DIFFERENT ELEMENTS
		if (ENABLE_MUTEX)
		{
			std::lock_guard<std::mutex> locker(m_mutex);
			m_image.pixelData[y][x] = value;
		}
		else
			m_image.pixelData[y][x] = value;
	}

	/*
		Saves image as BMP at 'filePath'
	*/
	void exportImage(std::string& filePath)
	{
		std::lock_guard<std::mutex> locker(m_mutex);
		std::ofstream newImageFile;
		newImageFile.open(filePath.c_str(), std::ios::binary);

		// write header to new image file
		newImageFile.write((char *)&m_image.header, sizeof(header_type));
		newImageFile.write((char *)&m_image.info, sizeof(information_type));

		// write new image data to new image file
		unsigned char tempData[3];
		for (int row = 0; row < m_image.info.height; row++) {
			for (int col = 0; col < m_image.info.width; col++) {
				tempData[0] = (unsigned char)m_image.pixelData[row][col];
				tempData[1] = (unsigned char)m_image.pixelData[row][col];
				tempData[2] = (unsigned char)m_image.pixelData[row][col];
				newImageFile.write((char *)tempData, 3 * sizeof(unsigned char));
			}
			if (m_image.padding) {
				tempData[0] = 0;
				tempData[1] = 0;
				tempData[2] = 0;
				newImageFile.write((char *)tempData, m_image.padding * sizeof(unsigned char));
			}
		}
		std::cout << filePath << " done." << std::endl;
		newImageFile.close();
	}

	/*
		Remove pixelData only
	*/
	void clear()
	{
		m_image.pixelData.clear();
		m_image.pixelData.resize(m_image.info.height);

		for (auto iter = m_image.pixelData.begin();
			iter != m_image.pixelData.end(); ++iter)
		{
			iter->resize(m_image.info.width);
		}
	}
};


/*
	Opens BMP file at 'filePath' and parses information into c++ structure
*/
bool extractImage(const std::string& filePath, Image& image)
{
	std::ifstream imageFile;
	imageFile.open(filePath.c_str(), std::ios::binary);
	if (!imageFile) {
		std::cerr << "file not found" << std::endl;
		return false;
	}

	// read file header
	imageFile.read((char *)&image.header, sizeof(header_type));
	if (image.header.id[0] != 'B' || image.header.id[1] != 'M') {
		std::cerr << "Does not appear to be a .bmp file" << std::endl;
		imageFile.close();
		return false;
	}

	// read/compute image information
	int row_bytes;
	imageFile.read((char *)&image.info, sizeof(information_type));
	row_bytes = image.info.width * 3;
	image.padding = row_bytes % 4;
	if (image.padding)
		image.padding = 4 - image.padding;

	// extract image data, initialize vectors
	unsigned char tempData[3];
	image.pixelData.reserve(image.info.height);

	for (int row = 0; row < image.info.height; row++) {
		image.pixelData.push_back(std::vector <int>());
		image.pixelData[row].reserve(image.info.width);

		for (int col = 0; col < image.info.width; col++) {
			imageFile.read((char *)tempData, 3 * sizeof(unsigned char));
			image.pixelData[row].push_back((int)tempData[0]);
		}
		if (image.padding)
			imageFile.read((char *)tempData, image.padding * sizeof(unsigned char));
	}
	std::cout << filePath << ": " << image.info.width << " x " << image.info.height << std::endl;

	imageFile.close();
	return true;
}


/*
	Apply sobel operator
*/
int sobel(const std::vector <std::vector <int> >& pixelData, int x, int y)
{
	int gx = (pixelData[y + 1][x + 1] + (pixelData[y][x + 1] * 2) + pixelData[y - 1][x + 1])
		- (pixelData[y + 1][x - 1] + (pixelData[y][x - 1] * 2) + pixelData[y - 1][x - 1]);

	int gy = (pixelData[y - 1][x - 1] + (pixelData[y - 1][x] * 2) + pixelData[y - 1][x + 1])
		- (pixelData[y + 1][x - 1] + (pixelData[y + 1][x] * 2) + pixelData[y + 1][x + 1]);

	return abs(gx) + abs(gy) > THRESHOLD ? 0 : 255;
}


/*
	Apply padding pixels to image - based on nearest pixel
*/
void padImage(Image& image)
{
	std::vector <std::vector <int> >& pixelDat = image.pixelData;
	
	for (auto iter = pixelDat.begin(); iter != pixelDat.end(); ++iter)
	{
		iter->insert(iter->begin(), iter->front());
		iter->push_back(iter->back());
	}

	pixelDat.insert(pixelDat.begin(), pixelDat.front());
	pixelDat.push_back(pixelDat.back());
}


/*
	Apply sobel operator over a specified range of rows
*/
void applyFilter(const Image& original, SharedImage& output,
	unsigned int start, unsigned int size)
{
	// "+ 1" is to compensate for padding around image
	for (unsigned int y = start + 1; y != start + size + 1; ++y)
	{
		for (int x = 1; x != original.info.width + 1; ++x)
		{
			output.setPixel(x - 1, y - 1, sobel(original.pixelData, x, y));
		}
	}
}


/*~~~~~~~~~~~~~~~~~~~ MAIN ~~~~~~~~~~~~~~~~~~~*/
int main(int argc, char* argv[])
{
	if (argc < 3)
	{
		std::cerr << "There should be two arguments. One with the path to image" 
			" file you want to analyze, one with the path to the output file." << std::endl;
		return -1;
	}

	unsigned int cores = std::thread::hardware_concurrency();
	std::cout << "Available cores: " << cores << std::endl;

	std::string inFilePath = argv[1];
	std::string outFilePath = argv[2];
	Image image;

	extractImage(inFilePath, image);

	padImage(image);

	SharedImage newImage(image.header, image.info, image.padding);
	boost::timer t;

	// Try for varying number of threads
	for (int nThreads = 1; nThreads < 11; ++nThreads)
	{
		// Record three times and take average
		std::vector<double> times;
		for (int round = 0; round < 3; ++round)
		{
			newImage.clear();

			// Start timer
			t.restart();

			int partitionSize = image.info.height / nThreads;
			std::vector<std::thread> threads;

			for (int i = 0; i < nThreads - 1; ++i)
			{
				threads.push_back(
					std::thread(applyFilter, std::ref(image), std::ref(newImage),
						partitionSize * i, partitionSize)
				);
			}

			int start = partitionSize * (nThreads - 1);
			applyFilter(std::ref(image), std::ref(newImage), start, image.info.height - start);

			for (auto it = threads.begin(); it != threads.end(); ++it)
			{
				it->join();
			}

			// Stop timer
			times.push_back(t.elapsed());
		}

		double tElapsed = (times[0] + times[1] + times[2]) / 3.0;
		std::cout << "Time to apply filter for " << nThreads << " threads: " << tElapsed << std::endl;
	}


	newImage.exportImage(outFilePath);
	return 0;
}
