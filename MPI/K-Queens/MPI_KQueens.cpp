/*
	@author: Matthew Lueder
	@description: Solves K-Queens problem by distributing work via MPI
	@date: 12/4/2016
*/
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <mpi.h>

#define K 1
#define MAX_SOLUTIONS 0 // Number of solutions we will be able to store per proc

static int funcCalls = 0;

/*
	Checks if a queen can be placed at (col, row)
	Returns true if no conflicts, false if it can't be placed
*/
bool Check_Spot(int queenPos[K], int row, int col)
{
	if (row >= K || col >= K) return false;

	for (int i = 0; i < col; ++i)
	{
		// Make sure no pieces in same row
		if (queenPos[i] == row) return false;

		// Make sure no queens on same positive diagnal
		if (queenPos[i] + i == row + col) return false;

		// Make sure no queens on negative diagnal
		if (queenPos[i] - i == row - col) return false;
	}

	return true;
}

/*
	Recursive function which tries to place a queen in the given column 
	and if successful, it calls itself for the next column. If it 
	fails to place the queen, it lets the parent call know, and 
	the queen from the column before is moved to a new position and 
	we try the call again.

*/
bool Place_Queen(int queenPos[K], int col, int solutions[MAX_SOLUTIONS][K], int& solNum)
{
	funcCalls++;
	
	int row = 0;
	bool placed = false;

	while (!placed)
	{ 
		while (!Check_Spot(queenPos, row, col)) {
			if (row == K-1) return false;
			row++;
		}

		queenPos[col] = row;

		// Queen placed successfully in last column = a solution
		if (col == K-1)
		{
			if (solNum < MAX_SOLUTIONS)
			{ 
				for (int i = 0; i < K; ++i)
				{
					solutions[solNum][i] = queenPos[i];
				}
			}
			solNum++;
		}

		placed = Place_Queen(queenPos, col+1, solutions, solNum);
		row++;
		if (row == K) return false;
	}
	return true;
}

/*
	Prints out chess board to console
*/
void Print_Board(int queenPos[K])
{
	int i,j;

	for (i = 0; i < K; ++i)
	{
		for (j = 0; j < K; ++j)
		{
			queenPos[j] == i ? printf("Q  ") : printf("_  ");
		}
		printf("\n");
	}
}


int main(int argc, char* argv[])
{
	double time;
	int solutions[MAX_SOLUTIONS][K];
	int my_rank, num_nodes;	
	int numSol = 0;

	MPI_Init(&argc, &argv);
	MPI_Comm_rank(MPI_COMM_WORLD, &my_rank);
	MPI_Comm_size(MPI_COMM_WORLD, &num_nodes);
	
	// Start time
	if (my_rank == 0) time = MPI_Wtime();
	
	// For now, one process per column exactly
	if (num_nodes != K) return 1;
	
	// Stores information on queen placement
	int queenPos[K] = {0};
	
	// Set first queen in first column with row based on process rank
	queenPos[0] = my_rank;
	
	Place_Queen(queenPos, 1, solutions, numSol);
	
	// Collect the number of solutions from all processes
	int totalSol = 0;
	MPI_Reduce(&numSol, &totalSol, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);
	
	// Collect the number of recursive function calls from all processes
	int totalFuncCalls = 0;
	MPI_Reduce(&funcCalls, &totalFuncCalls, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);
	
	if (my_rank == 0) {
		printf("Number of times 'Place_Queen' called: %d\n", totalFuncCalls);
		printf("Total solutions: %d\n" , totalSol);
		printf("Time elapsed: %f\n", MPI_Wtime() - time);
	}
	
	// Print out solutions in order
	for(int node = 0; node < num_nodes; ++node)
	{
		MPI_Barrier(MPI_COMM_WORLD);
		
		if (my_rank == node)
		{
			for (int i = 0; i < MAX_SOLUTIONS && i < numSol; ++i)
			{
				Print_Board(solutions[i]);
				printf("\n");
			}
		}
	}
	
	MPI_Finalize();

    return 0;
} 