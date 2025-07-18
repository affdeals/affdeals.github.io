// Amazon Affiliate Configuration
const AMAZON_CONFIG = {
    affiliateId: 'affdealsplus-21',
    baseUrl: 'https://www.amazon.in'
};

// Function to generate Amazon affiliate link
function generateAmazonLink(asin) {
    return `${AMAZON_CONFIG.baseUrl}/dp/${asin}?tag=${AMAZON_CONFIG.affiliateId}`;
}

// Function to get spec score background color based on score
function getSpecScoreColor(score) {
    if (score >= 90) return 'linear-gradient(135deg, #1e7e34, #28a745)'; // Dark green
    if (score >= 80) return 'linear-gradient(135deg, #28a745, #34ce57)'; // Medium-dark green
    if (score >= 70) return 'linear-gradient(135deg, #34ce57, #40d869)'; // Medium green
    if (score >= 60) return 'linear-gradient(135deg, #40d869, #51e57b)'; // Medium-light green
    if (score >= 50) return 'linear-gradient(135deg, #51e57b, #6bf28d)'; // Light green
    if (score >= 40) return 'linear-gradient(135deg, #6bf28d, #85ff9f)'; // Very light green
    return 'linear-gradient(135deg, #85ff9f, #a5ffb1)'; // Lightest green
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AMAZON_CONFIG, generateAmazonLink, getSpecScoreColor };
}