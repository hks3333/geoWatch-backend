import React, { useState, useEffect } from 'react';
import { Card, Button, Badge, Skeleton } from './common/ui';
import { DownloadIcon, FileTextIcon, Loader2Icon, AlertTriangleIcon } from './common/Icons';
import * as api from '../services/apiService';

interface ReportViewerProps {
    resultId: string;
    areaName: string;
}

interface Report {
    report_id: string;
    area_id: string;
    result_id: string;
    generated_at: string;
    summary: string;
    key_findings: string[];
    recommendations: string[];
    report_markdown: string;
    status: string;
}

const ReportViewer: React.FC<ReportViewerProps> = ({ resultId, areaName }) => {
    const [report, setReport] = useState<Report | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [showFullReport, setShowFullReport] = useState(false);

    useEffect(() => {
        fetchReport();
    }, [resultId]);

    const fetchReport = async () => {
        try {
            setLoading(true);
            setError(null);
            const reportData = await api.getResultReport(resultId);
            setReport(reportData);
        } catch (err) {
            setError('Failed to load report');
        } finally {
            setLoading(false);
        }
    };

    const downloadReport = () => {
        if (!report) return;

        const content = `# ${areaName} - Analysis Report\n\n${report.report_markdown}`;
        const blob = new Blob([content], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${areaName.replace(/\s+/g, '_')}_report_${report.report_id}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const downloadPDF = () => {
        if (!report) return;

        // Create a printable HTML version
        const printWindow = window.open('', '_blank');
        if (!printWindow) return;

        const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>${areaName} - Analysis Report</title>
                <style>
                    body {
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                        line-height: 1.6;
                        max-width: 800px;
                        margin: 40px auto;
                        padding: 20px;
                        color: #333;
                    }
                    h1 { color: #1a202c; border-bottom: 2px solid #4299e1; padding-bottom: 10px; }
                    h2 { color: #2d3748; margin-top: 30px; }
                    h3 { color: #4a5568; }
                    ul { padding-left: 20px; }
                    li { margin: 8px 0; }
                    .summary { background: #ebf8ff; padding: 15px; border-left: 4px solid #4299e1; margin: 20px 0; }
                    .finding { background: #f7fafc; padding: 10px; margin: 10px 0; border-radius: 4px; }
                    .recommendation { background: #fffaf0; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 3px solid #ed8936; }
                    @media print {
                        body { margin: 0; padding: 20px; }
                    }
                </style>
            </head>
            <body>
                <h1>${areaName} - Analysis Report</h1>
                <p><strong>Generated:</strong> ${new Date(report.generated_at).toLocaleString()}</p>
                <p><strong>Report ID:</strong> ${report.report_id}</p>
                
                <div class="summary">
                    <h2>Executive Summary</h2>
                    <p>${report.summary}</p>
                </div>

                <h2>Key Findings</h2>
                ${report.key_findings.map(f => `<div class="finding">• ${f}</div>`).join('')}

                <h2>Recommendations</h2>
                ${report.recommendations.map(r => `<div class="recommendation">• ${r}</div>`).join('')}

                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e2e8f0;">

                ${convertMarkdownToHTML(report.report_markdown)}
            </body>
            </html>
        `;

        printWindow.document.write(htmlContent);
        printWindow.document.close();
        setTimeout(() => {
            printWindow.print();
        }, 250);
    };

    const convertMarkdownToHTML = (markdown: string): string => {
        // Simple markdown to HTML converter
        let html = markdown;
        
        // Headers
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
        
        // Bold
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Lists
        html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
        html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
        
        // Paragraphs
        html = html.replace(/\n\n/g, '</p><p>');
        html = '<p>' + html + '</p>';
        
        return html;
    };

    if (loading) {
        return (
            <Card>
                <div className="flex items-center justify-center py-8">
                    <Loader2Icon className="h-8 w-8 animate-spin text-blue-500" />
                    <span className="ml-3 text-gray-600">Loading report...</span>
                </div>
            </Card>
        );
    }

    if (error || !report) {
        return (
            <Card>
                <div className="text-center py-8">
                    <AlertTriangleIcon className="h-12 w-12 mx-auto text-gray-400 mb-3" />
                    <h3 className="text-lg font-semibold text-gray-700">No Report Available</h3>
                    <p className="text-gray-500 mt-2">
                        {error || 'Report is being generated. Please check back in a few moments.'}
                    </p>
                </div>
            </Card>
        );
    }

    return (
        <Card>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                    <FileTextIcon className="h-6 w-6 text-blue-500 mr-2" />
                    <h3 className="text-xl font-bold">AI-Generated Analysis Report</h3>
                </div>
                <div className="flex items-center space-x-2">
                    <Badge variant="success">Generated</Badge>
                    <Button variant="outline" size="sm" onClick={downloadReport}>
                        <DownloadIcon className="h-4 w-4 mr-1" />
                        Markdown
                    </Button>
                    <Button variant="outline" size="sm" onClick={downloadPDF}>
                        <DownloadIcon className="h-4 w-4 mr-1" />
                        PDF
                    </Button>
                </div>
            </div>

            <p className="text-sm text-gray-500 mb-6">
                Generated on {new Date(report.generated_at).toLocaleString()}
            </p>

            {/* Executive Summary */}
            <div className="bg-blue-50 border-l-4 border-blue-500 p-4 mb-6">
                <h4 className="font-semibold text-blue-900 mb-2">Executive Summary</h4>
                <p className="text-blue-800">{report.summary}</p>
            </div>

            {/* Key Findings */}
            <div className="mb-6">
                <h4 className="font-semibold text-gray-900 mb-3">Key Findings</h4>
                <ul className="space-y-2">
                    {report.key_findings.map((finding, index) => (
                        <li key={index} className="flex items-start">
                            <span className="inline-block w-2 h-2 bg-blue-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                            <span className="text-gray-700">{finding}</span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Recommendations */}
            <div className="mb-6">
                <h4 className="font-semibold text-gray-900 mb-3">Recommendations</h4>
                <ul className="space-y-2">
                    {report.recommendations.map((rec, index) => (
                        <li key={index} className="flex items-start bg-orange-50 p-3 rounded border-l-3 border-orange-400">
                            <span className="inline-block w-2 h-2 bg-orange-500 rounded-full mt-2 mr-3 flex-shrink-0"></span>
                            <span className="text-gray-700">{rec}</span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Full Report Toggle */}
            <div className="border-t pt-4">
                <Button
                    variant="outline"
                    onClick={() => setShowFullReport(!showFullReport)}
                    className="w-full"
                >
                    {showFullReport ? 'Hide' : 'Show'} Full Detailed Report
                </Button>

                {showFullReport && (
                    <div className="mt-6 prose prose-sm max-w-none">
                        <div 
                            className="markdown-content"
                            dangerouslySetInnerHTML={{ __html: convertMarkdownToHTML(report.report_markdown) }}
                        />
                    </div>
                )}
            </div>
        </Card>
    );
};

export default ReportViewer;
