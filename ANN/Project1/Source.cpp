#include <vector>
#include <deque>
#include <iostream>
#include <fstream>
#include <list>
#include <cstdlib>
#include <ctime>
#include <armadillo>
#include <fstream>

// Leraning rate
#define L 0.2

class NeuralNet
{
	public:
		NeuralNet(int numLayers, int numNodesPerLayer, int numInputs, int numClasses)
		{
			m_numLayers = numLayers;
			m_numNodesPerLayer = numNodesPerLayer;
			m_numInputs = numInputs;
			m_numClasses = numClasses;

			m_weights = std::vector<arma::mat>();

			arma::arma_rng::set_seed_random();

			// Add input -> 1st layer weights
			m_weights.push_back(arma::randu<arma::mat>(numInputs+1,numNodesPerLayer) / 10);

			// Add hidden layer -> hidden layer weights
			for (int i = 0; i < numLayers - 1; ++i)
			{
				m_weights.push_back(arma::randu<arma::mat>(numNodesPerLayer+1, numNodesPerLayer) / 10);
			}

			// Add hidden layer -> output weights
			m_weights.push_back(arma::randu<arma::mat>(numNodesPerLayer + 1, numClasses) / 10);
		}

		// Testing class
		NeuralNet()
		{
			m_numLayers = 1;
			m_numNodesPerLayer = 2;
			m_numInputs = 2;
			m_numClasses = 1;

			m_weights = std::vector<arma::mat>();

			// Add input -> 1st layer weights
			arma::mat inputs(3, 2);
			inputs(0 ,0) = 1;
			inputs(0, 1) = -1;
			inputs(1, 0) = 0.5;
			inputs(1, 1) = 2;
			inputs(2, 0) = 1;
			inputs(2, 1) = 1;
			m_weights.push_back(inputs);

			// Add hidden layer -> output weights
			arma::mat hidden(3, 1);
			hidden(0, 0) = 1.5;
			hidden(1, 0) = -1;
			hidden(2, 0) = 1;
			m_weights.push_back(hidden);

			arma::rowvec features(2);
			features(0) = 0;
			features(1) = 1;
			
			backprop(features, 1);
		}

		int classify(arma::rowvec features)
		{
			return feedFoward(features).index_max();
		}

		arma::rowvec feedFoward(arma::rowvec features)
		{
			m_a.clear();

			// Multiply by weights for each layer
			arma::rowvec result = features;
			for (int i = 0; i <= m_numLayers; ++i)
			{
				// Add bias
				result.resize(result.n_elem + 1);
				result.at(result.n_elem - 1) = 1;
				m_a.push_back(result);

				result = result * m_weights[i];
				sigmoid(result);
			}

			return result;
		}

		void sigmoid(arma::rowvec& values)
		{ 
			values = 1 / (1 + arma::exp(values * -1));
		}

		void backprop(arma::rowvec features, int class_label)
		{
			std::deque<arma::mat> djdws;

			arma::rowvec actualY = arma::zeros<arma::rowvec>(m_numClasses);
			actualY(class_label) = 1;
			//arma::rowvec actualY(1); CODE FOR TESTING
			//actualY(0) = 1;

			arma::rowvec predY = feedFoward(features);

			// Derivative of sigmoid = sigmoid(weights[i] * input)(1 - sigmoid(weights * input))
			// Error of output units
			arma::rowvec delta = (actualY - predY) % (predY % (1 - predY));
			// Derivative of cost function
			arma::mat djdw = m_a.back().t() * delta;
			// Save derivative of cost so we can update weights later
			djdws.push_front(djdw);

			for (int i = m_weights.size() - 1; i > 0; --i)
			{
				// Error for hidden layer
  				delta = (delta * m_weights[i].t()) % (m_a[i] % (1 - m_a[i]));
				// Derivative of cost function
				djdw = m_a[i-1].t() * delta;
				// Save derivative of cost so we can update weights later + remove bias
				djdws.push_front(djdw.head_cols(djdw.n_cols - 1));
				// Remove bias so we can backpropagate to next layer
				delta = delta.head(delta.n_elem - 1);
			}

			// Update weights
			for (int i = m_weights.size() - 1; i >= 0; --i)
			{
				m_weights[i] = m_weights[i] + L * djdws[i];
			}

		}

		void train(arma::mat example_set, arma::ivec class_labels, int max_epochs)
		{
			for (int epoch = 0; epoch < max_epochs; ++epoch)
			{
				std::cout << "\r" << "Training epoch " << epoch;
				for (int i = 0; i < class_labels.n_elem; ++i)
					backprop(example_set.row(i), class_labels[i]);
			}
			std::cout << std::endl;
		}

		void createConfMatrix(arma::mat test_set, arma::ivec class_labels, int numClasses)
		{
			arma::imat conf = arma::zeros<arma::imat>(numClasses, numClasses);

			for (int i = 0; i < class_labels.n_elem; ++i)
			{
				int predY = classify(test_set.row(i));
				++conf.at(class_labels[i], predY);;
			}
			conf.save("C:\\Users\\Matthew\\Dropbox\\Machine Learning\\Projects\\Project4\\confusion-matrix.csv", arma::csv_ascii);
		}

		double testAccuracy(arma::mat test_set, arma::ivec class_labels, int numClasses)
		{
			int correct = 0;
			int wrong = 0;

			for (int i = 0; i < class_labels.n_elem; ++i)
			{
				int predY = classify(test_set.row(i));
				if (predY == class_labels[i])
				{
					++correct;
				}
				else
				{
					++wrong;
				}
			}
			return (double)correct / (double)(correct + wrong);
		}

		double totalNetworkError(arma::rowvec features, int class_label)
		{
			arma::rowvec actualY = arma::zeros<arma::rowvec>(m_numClasses);
			actualY(class_label) = 1;

			arma::rowvec predY = feedFoward(features);
			predY.print(std::cout);

			return arma::sum(0.5 * arma::square(actualY - predY));
		}

	private:
		int m_numLayers;
		int m_numNodesPerLayer;
		int m_numInputs;
		int m_numClasses;
		std::vector<arma::mat> m_weights;
		std::vector<arma::rowvec> m_a;
};

void loadData(std::string filepath, arma::mat& data_out, arma::ivec& classes_out)
{
	std::vector<std::vector<double>> allExamples = std::vector<std::vector<double>>();
	allExamples.reserve(5000);
	std::vector<int> classes = std::vector<int>();
	classes.reserve(5000);
	std::ifstream file(filepath); 
	std::string line;

	while (getline(file, line))
	{
		std::vector<double> example = std::vector<double>();
		int start = 0;
		int commaPos = 0;

		while (commaPos != std::string::npos)
		{ 
			commaPos = line.find(',', start);
			if (commaPos == std::string::npos)
			{
				classes.push_back(std::stoi(line.substr(start, commaPos - start)));
			}
			else 
			{
				example.push_back(std::stod(line.substr(start, commaPos - start)));
			}
			start = commaPos + 1;
		}
		allExamples.push_back(example);
	}

	data_out.set_size(allExamples.size(), allExamples.front().size());
	for (int i = 0; i != allExamples.size(); ++i)
	{
		for (int j = 0; j != allExamples[i].size(); ++j)
		{
			data_out.at(i, j) = allExamples[i][j];
		}
	}

	classes_out.set_size(classes.size());
	for (int i = 0; i != classes.size(); ++i)
	{
		classes_out.at(i) = classes[i];
	}
}

int main()
{
	// Load in training data
	arma::mat trainingSet;
	arma::ivec training_lbls;
	loadData("C:\\Users\\Matthew\\Dropbox\\Machine Learning\\Projects\\Project4\\digits-training.data", 
		trainingSet, training_lbls);
	trainingSet = trainingSet / 16;
	// Load in test data
	arma::mat testSet;
	arma::ivec test_lbls;
	loadData("C:\\Users\\Matthew\\Dropbox\\Machine Learning\\Projects\\Project4\\digits-test.data",
		testSet, test_lbls);
	testSet = testSet / 16;

	arma::ivec classes = arma::unique(training_lbls);

	NeuralNet net = NeuralNet(1, 80, trainingSet.n_cols, classes.n_elem);
	net.train(trainingSet, training_lbls, 5000);
	net.createConfMatrix(testSet, test_lbls, classes.n_elem);
	std::cout << net.testAccuracy(testSet, test_lbls, classes.n_elem) << std::endl;

	return 0;
}