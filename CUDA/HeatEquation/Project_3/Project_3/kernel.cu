/*
	@author Matthew Lueder
	@description Apply heat equation to arrays of varying sizes and dimensionality with CUDA
*/

#include "cuda_runtime.h"
#include "device_launch_parameters.h"
#include <stdio.h>
#include <stdlib.h>
#include <math.h>  
#include <boost\timer.hpp>
#include "CImg.h"

using namespace cimg_library;

/* CONTROLS / SWITCHS */

// So we can experiment with differnt precision
typedef float floatp;

// For all implementations
#define ITERATIONS 100000 
#define H_HEAT 100.00
#define H_ROOM_TEMP 23.00
__constant__ floatp HEAT = H_HEAT;
__constant__ floatp ROOM_TEMP = H_ROOM_TEMP;

// For 1-D multi-block implementation
#define H_NUM_SLICES 1000000
__constant__ size_t D_NUM_SLICES = H_NUM_SLICES;

// For 2-D implementation
#define H_ROOM_X 1000
#define H_ROOM_Y 1000
#define STEPS 1
#define DRAW_IMG false
__constant__ int ROOM_X = H_ROOM_X;
__constant__ int ROOM_Y = H_ROOM_Y;

// Macros
#define ROOM_INDEX(_x, _y) (_x) + ROOM_X * (_y)
#define GLOBAL_INDEX(_x,_y) (_y) * (gridDim.x * blockDim.x) + (_x)
#define LOCAL_INDEX(_x,_y) (_y) * blockDim.x + (_x)
#define CHECK(cudaStatus) if(cudaStatus != cudaSuccess) printf("%d> CUDA ERROR: %s\n", __LINE__, cudaGetErrorString(cudaStatus))

/*
	This kernel initializes rods in device memory
*/
__global__ void  initialize(floatp *rod)
{
	// Get unique id
	int id = blockIdx.x * blockDim.x + threadIdx.x;

	// Set first element to HEAT, and all others to ROOM_TEMP
	if (id < D_NUM_SLICES && id != 0)
	{
		rod[id] = ROOM_TEMP;
	}
	else if (id == 0)
	{
		rod[0] = HEAT;
	}
}

/*
This kernel initializes rooms in device memory
*/
__global__ void  initialize2D(floatp* room)
{
	// Get x and y value
	int x = blockIdx.x * blockDim.x + threadIdx.x;
	int y = blockIdx.y * blockDim.y + threadIdx.y;

	// Set first element to HEAT, and all others to ROOM_TEMP
	if (x < ROOM_X && y < ROOM_Y)
	{
		int room_index = ROOM_INDEX(x, y);

		if (room_index == 0)
		{
			room[0] = HEAT;
		}
		else
		{
			room[room_index] = ROOM_TEMP;
		}
	}
}

/*
	Multi-block solution which uses a combination of shared and global memory. 
	Can handle larger input arrays.
	Running this kernel once is the equivalent of going foward one time step.
*/
__global__ void applyHeat(floatp* rod_in, floatp* rod_out)
{
	extern __shared__ floatp sharedMem[];

	// Get unique id
	int uid = (blockIdx.x * blockDim.x + threadIdx.x) + 1;

	// Thread id
	int tid = threadIdx.x;

	// Load global data to shared data
	if (uid < D_NUM_SLICES)
		sharedMem[tid] = rod_in[uid];

	__syncthreads();

	if (uid < (D_NUM_SLICES-1))
	{ 
		if (tid == 0)
		{
			rod_out[uid] = (rod_in[uid-1] + sharedMem[tid+1]) / 2;
		}
		else if (tid == blockDim.x - 1)
		{
			rod_out[uid] = (rod_in[uid+1] + sharedMem[tid-1]) / 2;
		}
		else
		{
			rod_out[uid] = (sharedMem[tid-1] + sharedMem[tid+1]) / 2;
		}
	}
	else if (uid == (D_NUM_SLICES - 1))
	{
		if (tid != 0)
		{
			rod_out[uid] = (sharedMem[tid-1] + sharedMem[tid]) / 2;
		}
		else
		{
			rod_out[uid] = (rod_in[uid-1] + sharedMem[tid]) / 2;
		}
	}
}


/*
	1-block solution which only uses shared memory and executes multiple time steps in one kernel call.
	This solution is limited to arrays of size 1024 / 1024 threads per block.
	No need to initialize (done in this kernel).
	Super fast but very limited.
*/
__global__ void applyHeat(floatp* rod)
{
	 __shared__ floatp sMem[1025];
	 __shared__ floatp sMem2[1025];

	// Thread id (1-1024)
	int id = threadIdx.x + 1;

	// Set heat source
	if (id == 1)
	{ 
		sMem[0] = HEAT;
		sMem2[0] = HEAT;
	}

	// Set elements to room temp
	sMem[id] = ROOM_TEMP;

	__syncthreads();

	int iteration = 0;
	while (iteration < ITERATIONS)
	{ 
		if (iteration % 2 == 0)
		{ 
			if (id != 1024)
			{
				sMem2[id] = (sMem[id - 1] + sMem[id + 1]) / 2;
			}
			else
			{
				sMem2[id] = (sMem[id - 1] + sMem[id]) / 2;
			}
		}
		else
		{
			if (id != 1024)
			{
				sMem[id] = (sMem2[id - 1] + sMem2[id + 1]) / 2;
			}
			else
			{
				sMem[id] = (sMem2[id - 1] + sMem2[id]) / 2;
			}
		}
		
		__syncthreads();
		++iteration;
	}

	if (iteration % 2 == 0)
	{ 
		rod[id - 1] = sMem[id];
	}
	else
	{
		rod[id - 1] = sMem2[id];
	}
}


/*
	Multi-block solution which uses a combination of shared and global memory.
	Running this kernel once is the equivalent of going foward one time step.
	Use square blocks (32x32) only.
*/
__global__ void applyHeat2D(floatp* room_in, floatp* room_out)
{
	__shared__ floatp sMem[1024];

	// Get X and Y relative to global block -> use to calculate room index
	int x = blockIdx.x * blockDim.x + threadIdx.x;
	int y = blockIdx.y * blockDim.y + threadIdx.y;
	int pos = ROOM_INDEX(x,y);

	// Unique id for threads in block
	int t_x = threadIdx.x;
	int t_y = threadIdx.y;
	int t_pos = LOCAL_INDEX(t_x, t_y);

	__syncthreads();

	// Ignore threads outside of room boundaries
	if (x < ROOM_X && y < ROOM_Y)
	{ 
		// Load global data to shared data
		sMem[t_pos] = room_in[pos];

		__syncthreads();

		// Elements needed to perform calculation
		floatp top, bottom, left, right;
		
		// ~ Find top element ~
		if (t_y == 0)
		{
			if (y == 0)
			{
				// top element is a wall of the room (re-use this element's data)
				top = sMem[t_pos];
			}
			else
			{
				// top element in room but beyond block boundry
				top = room_in[ROOM_INDEX(x, y-1)];
			}
		}
		else
		{
			// top element within room and block
			top = sMem[LOCAL_INDEX(t_x, t_y-1)];
		}

		// ~ Find bottom element ~
		if (y == ROOM_Y - 1)
		{
			// Bottom element is the wall of the room
			bottom = sMem[t_pos];
		}
		else if (t_y == blockDim.y - 1)
		{
			// Bottom element is in room but beyond block boundry
			bottom = room_in[ROOM_INDEX(x, y+1)];
		}
		else
		{
			// Bottom element in block and room
			bottom = sMem[LOCAL_INDEX(t_x, t_y+1)];
		}

		// ~ Find left element ~
		if (x == 0)
		{
			// Left element is the wall of room
			left = sMem[t_pos];
		}
		else if (t_x == 0)
		{
			// Left element beyond block boundry
			left = room_in[ROOM_INDEX(x-1, y)];
		}
		else
		{
			// Left element in block and room
			left = sMem[LOCAL_INDEX(t_x-1, t_y)];
		}

		// ~ Find right element ~
		if (x == ROOM_X - 1)
		{
			// Right element is wall of room
			right = sMem[t_pos];
		}
		else if (t_x == blockDim.x - 1)
		{
			// Right element is beyond block boundry
			right = room_in[ROOM_INDEX(x+1, y)];
		}
		else
		{
			// Right element is in block and room
			right = sMem[LOCAL_INDEX(t_x+1, t_y)];
		}

		// Now we calculate the new tempurature
		if (pos != 0)
			room_out[pos] = (top + bottom + right + left) / 4;
	}
}

void DrawImage(floatp* room, int height, int width, int num)
{
	CImg<unsigned char> img(width, height, 1, 3, 255);
	
	for (int i = 0; i < height; ++i)
	{
		for (int j = 0; j < width; ++j)
		{
			floatp value = room[j + i * width];

			// Get normalized data point [0,1]
			floatp scaledVal = (value - H_ROOM_TEMP) / (H_HEAT - H_ROOM_TEMP);

			// Calculate color
			unsigned char color[3];
			color[0] = scaledVal * 225;
			color[1] = 0;
			color[2] = 225 + scaledVal * -225;
			img.draw_point(j, i, color);
		}
	}

	img.save("images/heatmap.bmp", num);
}

void OneBlockHeat()
{
	cudaError_t cudaStatus;
	const size_t SLICES = 1024;
	size_t size = SLICES * sizeof(floatp);

	// START TIMER
	boost::timer t;

	// Allocate space for return rod
	floatp* d_rod = NULL;
	cudaStatus = cudaMalloc((void**)&d_rod, size);
	CHECK(cudaStatus);

	// # Threads/blocks always the same for this kernel
	int threadsPerBlock = 1024;
	int blocksPerGrid = 1;

	// Perform kernel operation
	applyHeat <<< blocksPerGrid, threadsPerBlock >>> (d_rod);
	cudaStatus = cudaGetLastError();
	CHECK(cudaStatus);

	// PRINT TIME ELAPSED
	cudaDeviceSynchronize();
	printf("Time elapsed: %f\n", t.elapsed());

	// Pull rod into host for testing
	floatp* h_rod = (floatp *)malloc(size);
	cudaStatus = cudaMemcpy(h_rod, d_rod, size, cudaMemcpyDeviceToHost);
	CHECK(cudaStatus);

	for (int i = 0; i <= 10; i += 1)
	{
		printf("%f\t", h_rod[i]);
	}
	printf("\n");
	printf("%f\n", h_rod[SLICES - 1]);

	int ind = 0;
	while (abs(h_rod[ind] - 23.00) > 0.0001)
	{
		++ind;
	}
	printf("first untouched = %d\n", ind);

	cudaFree(d_rod);
	free(h_rod);

	// cudaDeviceReset must be called before exiting in order for profiling and
	// tracing tools such as Nsight and Visual Profiler to show complete traces.
	CHECK(cudaDeviceReset());
}

void MultiBlockHeat()
{
	cudaError_t cudaStatus;
	size_t size = H_NUM_SLICES * sizeof(floatp);

	// START TIMER
	boost::timer t;

	// Allocate space for Rods
	floatp* d_rod = NULL;
	cudaStatus = cudaMalloc((void**)&d_rod, size);
	CHECK(cudaStatus);

	floatp* d_rod2 = NULL;
	cudaStatus = cudaMalloc((void**)&d_rod2, size);
	CHECK(cudaStatus);

	// Calculate threads/blocks for initialize kernel
	int threadsPerBlock = 1024;
	int blocksPerGrid = H_NUM_SLICES / threadsPerBlock;
	if (H_NUM_SLICES % threadsPerBlock != 0)
		++blocksPerGrid;

	// Perform initialize kernel
	printf("CUDA 'initialize' kernel launch with %d blocks of %d threads\n", blocksPerGrid, threadsPerBlock);
	initialize <<< blocksPerGrid, threadsPerBlock >>> (d_rod);
	initialize <<< blocksPerGrid, threadsPerBlock >>> (d_rod2);
	cudaStatus = cudaGetLastError();
	CHECK(cudaStatus);

	// Calculate blocks per grid for apply heat kernel
	blocksPerGrid = (H_NUM_SLICES - 1) / threadsPerBlock;
	if ((H_NUM_SLICES - 1) % threadsPerBlock != 0)
		++blocksPerGrid;

	// Perform applyHeat kernel for a specified number of iterations (time steps)
	printf("CUDA 'applyHeat' kernel launch with %d blocks of %d threads\n", blocksPerGrid, threadsPerBlock);
	int iteration = 0;
	while (iteration < ITERATIONS)
	{
		if (iteration % 2 == 0)
		{
			applyHeat <<< blocksPerGrid, threadsPerBlock, threadsPerBlock * sizeof(floatp) >>> (d_rod, d_rod2);
		}
		else
		{
			applyHeat <<< blocksPerGrid, threadsPerBlock, threadsPerBlock * sizeof(floatp) >>> (d_rod2, d_rod);
		}

		cudaDeviceSynchronize();
		++iteration;
	}

	cudaStatus = cudaGetLastError();
	CHECK(cudaStatus);

	// PRINT TIME ELAPSED
	printf("Time elapsed: %f\n", t.elapsed());

	// Pull rod into host for testing
	floatp* h_rod = (floatp *)malloc(size);
	cudaStatus = cudaMemcpy(h_rod, d_rod, size, cudaMemcpyDeviceToHost);
	CHECK(cudaStatus);

	for (int i = 0; i <= 10; i += 1)
	{
		printf("%f\t", h_rod[i]);
	}
	printf("\n");
	printf("%f\n", h_rod[H_NUM_SLICES - 1]);

	int ind = 0;
	while (abs(h_rod[ind] - 23.00) > 0.0001)
	{
		++ind;
	}
	printf("first untouched = %d\n", ind);

	// Free memory
	cudaFree(d_rod);
	cudaFree(d_rod2);
	free(h_rod);

	// cudaDeviceReset must be called before exiting in order for profiling and
	// tracing tools such as Nsight and Visual Profiler to show complete traces.
	CHECK(cudaDeviceReset());
}

void Heat2D()
{
	cudaError_t cudaStatus;
	size_t size = H_ROOM_X * H_ROOM_Y * sizeof(floatp);

	// START TIMER
	boost::timer t;

	// Allocate space for rooms
	floatp* d_room = NULL;
	cudaStatus = cudaMalloc((void**)&d_room, size);
	CHECK(cudaStatus);

	floatp* d_room2 = NULL;
	cudaStatus = cudaMalloc((void**)&d_room2, size); // TEST WITH PADDING
	CHECK(cudaStatus);

	// Calculate threads/blocks for initialize kernel
	dim3 blockDims(32, 32, 1);

	int xBlocks = H_ROOM_X / 32;
	if (H_ROOM_X % 32 != 0)
		++xBlocks;
	int yBlocks = H_ROOM_Y / 32;
	if (H_ROOM_Y % 32 != 0)
		++yBlocks;
	dim3 gridDims(xBlocks, yBlocks, 1);

	// Perform initialize kernel
	printf("CUDA 'intitialize2D' kernel launch with %d x %d blocks of %d x %d threads\n",
		gridDims.x, gridDims.y, blockDims.x, blockDims.y);

	initialize2D <<< gridDims, blockDims >>> (d_room);
	initialize2D <<< gridDims, blockDims >>> (d_room2);

	cudaStatus = cudaGetLastError();
	CHECK(cudaStatus);

	// Perform applyHeat kernel for a specified number of iterations (time steps)
	printf("CUDA 'applyHeat2D' kernel launch with %d x %d blocks of %d x %d threads\n", 
		gridDims.x, gridDims.y, blockDims.x, blockDims.y);

	// Save initial image
	floatp* h_room = (floatp *)malloc(size);
	cudaStatus = cudaMemcpy(h_room, d_room, size, cudaMemcpyDeviceToHost);
	CHECK(cudaStatus);
	DrawImage(h_room, H_ROOM_Y, H_ROOM_X, 0);

	// Divide up iterations
	for (int step = 0; step != STEPS; ++step)
	{ 
		int iteration = 0;
		while (iteration < ITERATIONS / STEPS)
		{
			if (iteration % 2 == 0)
			{
				applyHeat2D <<< gridDims, blockDims >>> (d_room, d_room2);
			}
			else
			{
				applyHeat2D <<< gridDims, blockDims >>> (d_room2, d_room);
			}

			cudaDeviceSynchronize();
			++iteration;
		}
		cudaStatus = cudaGetLastError();
		CHECK(cudaStatus);

		// Draw image
		if (DRAW_IMG)
		{ 
			h_room = (floatp *)malloc(size);
			cudaStatus = cudaMemcpy(h_room, d_room, size, cudaMemcpyDeviceToHost);
			CHECK(cudaStatus);
			DrawImage(h_room, H_ROOM_Y, H_ROOM_X, step+1);
		}
	}

	// PRINT TIME ELAPSED
	printf("Time elapsed: %f\n", t.elapsed());

	// Free memory
	cudaFree(d_room);
	cudaFree(d_room2);
	free(h_room);

	// cudaDeviceReset must be called before exiting in order for profiling and
	// tracing tools such as Nsight and Visual Profiler to show complete traces.
	CHECK(cudaDeviceReset());
}



int main(int argc, char* argv[])
{ 
	//OneBlockHeat();
	MultiBlockHeat();
	//Heat2D();

    return 0;
}

