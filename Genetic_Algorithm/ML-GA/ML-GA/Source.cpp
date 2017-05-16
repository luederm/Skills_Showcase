#include <bitset>
#include <random>
#include <iostream>
#include <utility>
#include <math.h>
#include <algorithm>
#include <map>
#include <fstream>
#include <time.h>

#define X_MAX 2.0f
#define X_MIN -2.0f
#define Y_MAX 2.0f
#define Y_MIN -2.0f

#define RECOMBINATION_RATE 0.60f
#define SNP_RATE 0.05f
#define NORMAL_MUT_RATE 0.4f
#define NORMAL_MUT_SD 0.01f

//#define ROSENBOCK

/* Function which evaulates fitness */
float fitness(float x, float y)
{
#ifdef ROSENBOCK
	float rosenbock = pow(1 - x, 2) + 100 * pow((y - pow(x, 2)), 2);
	return -rosenbock;
#else
	float gp = (pow(x+y+1,2) * (19 - 14 * x + 3 * pow(x,2) - 14 * y + 6 * x * y + 3 * pow(y,2))+1) 
		* (pow(2*x-3*y,2) * (18 - 32 * x + 12 * pow(x,2) + 48 * y - 36 * x * y + 27 * pow(y,2))+30);
	return -gp;
#endif 
}

/* For converting int representation to float */
union Flint 
{
	float f;
	unsigned long long i;
};

/* Allows for binary search roullette wheel to generate a new population in O(n log n) time */
struct Range
{
	Range(float start, float end) : start(start), end(end)
	{}

	friend bool operator< (const Range &r1, const Range &r2)
	{
		return r1.start < r2.start && r1.end < r2.end;
	}

	float start;
	float end;
};

class BinaryChromosome
{
public:
	/* Initializes with given number */
	BinaryChromosome(float init)
	{
		m_bits = std::bitset<sizeof(float)*CHAR_BIT>(*reinterpret_cast<unsigned long*>(&init));
	}

	/* Return floating point representation */
	float asFloat()
	{
		Flint flint;
		flint.i = m_bits.to_ullong();
		return flint.f;
	}

	/* Return string representation */
	std::string asString()
	{
		return m_bits.to_string();
	}

	int size()
	{
		return m_bits.size();
	}

	/* Induce single bit mutation at 'pos' */
	void induceSnp(const int pos)
	{
		m_bits.flip(pos);
	}

	/* Change bits to represent number */
	void changeTo(float newValue)
	{
		m_bits = std::bitset<sizeof(float)*CHAR_BIT>(*reinterpret_cast<unsigned long*>(&newValue));
	}

	/* Perform recomination on the leftmost 'position' bits */
	friend void crossover(BinaryChromosome &chrom1, BinaryChromosome &chrom2, const int position)
	{
		for (int i = 0; i != position; ++i)
		{
			bool oldBit = chrom1.m_bits[i];
			chrom1.m_bits[i] = chrom2.m_bits[i];
			chrom2.m_bits[i] = oldBit;
		}
	}


private:
	std::bitset<sizeof(float)*CHAR_BIT> m_bits;
};


class Individual
{
public:
	Individual(float x, float y) : m_x(x), m_y(y)
	{
		calcFitness();
	}

	/* Return pair of x,y values */
	std::pair<float, float> values_float()
	{
		return std::make_pair(m_x.asFloat(), m_y.asFloat());
	}

	/* Return pair of x,y values */
	std::pair<std::string, std::string> values_string()
	{
		return std::make_pair(m_x.asString(), m_y.asString());
	}

	float getFitness()
	{
		return m_fitness;
	}

	/* Induces snp on selected chrom and pos - if result is invalid, switch back and return false */
	bool induceSnp(const char chrom, const int pos)
	{
		if (chrom == 'X')
		{
			m_x.induceSnp(pos);
			float newVal = m_x.asFloat();
			if (newVal > X_MAX || newVal < X_MIN || newVal != newVal)
			{
				// switch back, return false
				m_x.induceSnp(pos);
				return false;
			}
		}
		else if (chrom == 'Y')
		{
			m_y.induceSnp(pos);
			float newVal = m_y.asFloat();
			if (newVal > Y_MAX || newVal < Y_MIN || newVal != newVal)
			{
				// switch back, return false
				m_y.induceSnp(pos);
				return false;
			}
		}
		calcFitness();
		return true;
	}

	/* Mutate float to desired value (Checks is in range, if not returns false) */
	bool mutate(const char chrom, const float newVal)
	{
		if (chrom == 'X')
		{
			if (newVal > X_MAX || newVal < X_MIN || newVal != newVal)
			{
				return false;
			}
			else
			{
				m_x.changeTo(newVal);
			}
		}
		else if (chrom == 'Y')
		{
			if (newVal > Y_MAX || newVal < Y_MIN || newVal != newVal)
			{
				return false;
			}
			else
			{
				m_y.changeTo(newVal);
			}
		}
		calcFitness();
		return true;
	}

	/* Allows sorting based on fitness */
	friend bool operator< (const Individual &i1, const Individual &i2)
	{
		return i1.m_fitness < i2.m_fitness;
	}

	/* Perform crossover operation between two individuals - if result is invalid, switch back and return false */
	friend bool crossover(Individual &i1, Individual &i2, const char chrom, const int pos)
	{
		if (chrom == 'X')
		{
			crossover(i1.m_x, i2.m_x, pos);
			float newVal1 = i1.m_x.asFloat();
			float newVal2 = i2.m_x.asFloat();
			if (newVal1 > X_MAX || newVal1 < X_MIN || newVal2 > X_MAX 
				|| newVal2 < X_MIN || newVal1 != newVal1 || newVal2 != newVal2)
			{
				// switch back, return false
				crossover(i1.m_x, i2.m_x, pos);
				return false;
			}

		}
		else if (chrom == 'Y')
		{
			crossover(i1.m_y, i2.m_y, pos);
			float newVal1 = i1.m_y.asFloat();
			float newVal2 = i2.m_y.asFloat();
			if (newVal1 > Y_MAX || newVal1 < Y_MIN || newVal2 > Y_MAX || 
				newVal2 < Y_MIN || newVal1 != newVal1 || newVal2 != newVal2)
			{
				// switch back, return false
				crossover(i1.m_y, i2.m_y, pos);
				return false;
			}
		}
		i1.calcFitness();
		i2.calcFitness();
		return true;
	}

private:
	/* Update individual's fitness - Call this function everytime individual is changed */
	void calcFitness()
	{
		m_fitness = fitness(m_x.asFloat(), m_y.asFloat());
	}

	BinaryChromosome m_x;
	BinaryChromosome m_y;
	float m_fitness;
};


class Population
{
public:
	Population(int size) : m_size(size), m_generation(0)
	{
		m_gen.seed(time(NULL));

		std::uniform_real_distribution<float> xDist(X_MIN, X_MAX);
		std::uniform_real_distribution<float> yDist(Y_MIN, Y_MAX);

		m_individuals = std::vector<Individual>();
		m_individuals.reserve(size);
		for (int i = 0; i < size; ++i)
		{
			m_individuals.push_back(Individual(xDist(m_gen), yDist(m_gen)));
		}
	}

	void evaluate()
	{
		std::sort(m_individuals.begin(), m_individuals.end());
		float meanfitness = 0;
		for (int i = m_size - 1; i>=0; --i)
		{
			meanfitness += m_individuals[i].getFitness();
		}
		meanfitness = meanfitness / m_size;

		std::cout << m_individuals.back().values_float().first << ", " << m_individuals.back().values_float().second << '\n';
		std::cout << m_individuals.back().values_string().first << ", " << m_individuals.back().values_string().second << '\n';
		std::cout << m_individuals.back().getFitness() << '\n';
		std::cout << meanfitness << '\n';
	}

	/* Write new line with (Best solution fitness, Average fitness) to a CSV file */
	void writeToCsv(std::ofstream& csv)
	{
		std::sort(m_individuals.begin(), m_individuals.end());

		float meanfitness = 0;
		for (int i = m_size - 1; i >= 0; --i)
		{
			meanfitness += m_individuals[i].getFitness();
		}
		meanfitness = meanfitness / m_size;

		csv << m_individuals.back().getFitness() << ',' << meanfitness << ",(" << 
			m_individuals.back().values_float().first << " - " << 
			m_individuals.back().values_float().second << ")\n";
	}

	/* Go through a generation - produces a new set of individuals */
	void generation()
	{
		std::sort(m_individuals.begin(), m_individuals.end());

		// Save elitist 
		Individual elite = m_individuals.back();

		// Get min for feature scaling
		float minFit = std::numeric_limits<float>::max();
		for (auto iter = m_individuals.begin(); iter != m_individuals.end(); ++iter)
		{
			float fitness = iter->getFitness();
			if (fitness > std::numeric_limits<float>::min())
			{ 
				if (fitness < minFit && iter->getFitness()) minFit = fitness;
			}
		}

		// Perform feature scaling and calculate total fitness
		double totalFitness = 0;
		std::vector<float> scaledFitness;
		scaledFitness.reserve(m_size);
		for (auto iter = m_individuals.begin(); iter != m_individuals.end(); ++iter)
		{
			float scaled = (iter->getFitness() - minFit);
			scaledFitness.push_back(scaled);
			totalFitness += scaled;
		}

		// Build weight vector
		std::vector<Range> weights;
		weights.reserve(m_size);
		float last = 0;

		// Get probabilities using proportional fitness selection and create a range 
		for (auto iter = scaledFitness.rbegin(); iter != scaledFitness.rend(); ++iter)
		{
			float next = last + (*iter / totalFitness);
			weights.push_back(Range(last, next));
			last = next;
		}

		std::vector<Individual> selected;
		selected.reserve(m_size);
		std::uniform_real_distribution<float> uRealDist(0.3, weights.back().end);

		// locate the random values based on the weights
		for (int j = 0; j < m_size; ++j)
		{
			float value = uRealDist(m_gen);
			auto found = std::lower_bound(weights.begin(), weights.end(), Range(value, value));
			int index = found - weights.begin();
			selected.push_back(m_individuals[index]);
		}

		// Save selected individuals as new member
		std::swap(selected, m_individuals);

		// We now have a vector of selected individuals in a random order.
		// The next step is to induce genetic variation
		std::uniform_int_distribution<int> uBoolDist(0, 1);
		std::uniform_int_distribution<int> uIntDist(0, sizeof(float)*CHAR_BIT - 1);
		std::uniform_int_distribution<int> uIntDist2(0, m_size - 1);

		// Recombination
		int numRecomb = floor(RECOMBINATION_RATE * m_size);
		int r = 0;
		while (r < numRecomb)
		{
			int ichrom = uBoolDist(m_gen);
			char chrom = 'X';
			if (ichrom) chrom == 'Y';

			if (crossover(m_individuals[uIntDist2(m_gen)], m_individuals[uIntDist2(m_gen)], chrom, uIntDist(m_gen))) ++r;
		}

		// SNPs
		int numSnps = floor(SNP_RATE * m_size);
		int i = 0;
		while (i < numSnps)
		{
			int ichrom = uBoolDist(m_gen);
			char chrom = 'X';
			if (ichrom) chrom == 'Y';

			if (m_individuals[uIntDist2(m_gen)].induceSnp(chrom, uIntDist(m_gen))) ++i;
		}

		// Ranged mutations based on normal distribution
		int numMut = floor(NORMAL_MUT_RATE * m_size);
		int m = 0;
		while (m < numMut)
		{
			int index = uIntDist2(m_gen);

			int ichrom = uBoolDist(m_gen);
			char chrom = 'X';
			if (ichrom) chrom == 'Y';

			float mean;
			if (chrom == 'X') {
				mean = m_individuals[index].values_float().first;
			}
			else {
				mean = m_individuals[index].values_float().second;
			}
			
			std::normal_distribution<float> norm(mean, NORMAL_MUT_SD);

			if (m_individuals[index].mutate(chrom, norm(m_gen))) ++m;
		}

		// Replace a random value with elite
		m_individuals[0] = elite;

		m_generation++;
	}

private:
	int m_size;
	int m_generation;
	std::default_random_engine m_gen;
	std::vector<Individual> m_individuals;
};


int main()
{
	Population p(50000);
	std::ofstream csv;
	csv.open("C:\\Users\\Matthew\\Desktop\\Delete\\OutputStats.csv");
	csv << "BestFitness,MeanFitness,BestValues\n";
	p.writeToCsv(csv);

	for (int i = 0; i < 100; ++i)
	{
		if (i % 10 == 0) std::cout << i << std::endl;
		p.generation();
		p.writeToCsv(csv);
	}

	return 0;
}