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
        let html = markdown;
        
        // Headers (must be done before paragraphs)
        html = html.replace(/^### (.*?)$/gm, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>');
        html = html.replace(/^## (.*?)$/gm, '<h2 class="text-xl font-bold mt-6 mb-3 border-b pb-2">$1</h2>');
        html = html.replace(/^# (.*?)$/gm, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>');
        
        // Bold and italic
        html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>');
        html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Code blocks
        html = html.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 p-3 rounded my-2 overflow-x-auto"><code>$1</code></pre>');
        html = html.replace(/`(.*?)`/g, '<code class="bg-gray-100 px-2 py-1 rounded text-sm">$1</code>');
        
        // Lists - handle both - and * prefixes
        const lines = html.split('\n');
        let inList = false;
        let listHtml = '';
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];
            if (line.match(/^[\s]*[-*] /)) {
                if (!inList) {
                    listHtml += '<ul class="list-disc list-inside my-2 space-y-1">';
                    inList = true;
                }
                const content = line.replace(/^[\s]*[-*] /, '');
                listHtml += `<li class="text-gray-700">${content}</li>`;
            } else {
                if (inList) {
                    listHtml += '</ul>';
                    inList = false;
                }
                listHtml += line + '\n';
            }
        }
        if (inList) {
            listHtml += '</ul>';
        }
        html = listHtml;
        
        // Line breaks
        html = html.replace(/\n\n+/g, '</p><p>');
        html = html.replace(/\n/g, '<br>');
        
        // Wrap remaining text in paragraphs
        const parts = html.split(/<\/?p>/);
        html = parts.map((part, i) => {
            if (part.trim() && !part.match(/^<[h|u|p|pre]/)) {
                return `<p class="text-gray-700 leading-relaxed my-2">${part}</p>`;
            }
            return part;
        }).join('');
        
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
            {report.key_findings && report.key_findings.length > 0 && (
                <div className="mb-6">
                    <h4 className="font-semibold text-gray-900 mb-3 text-base">Key Findings</h4>
                    <div className="space-y-2">
                        {report.key_findings.map((finding, index) => (
                            <div key={index} className="flex items-start gap-3 p-3 bg-blue-50 rounded-lg border border-blue-100">
                                <span className="inline-block w-1.5 h-1.5 bg-blue-600 rounded-full mt-2 flex-shrink-0"></span>
                                <span className="text-gray-700 text-sm leading-relaxed">{finding}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Recommendations */}
            {report.recommendations && report.recommendations.length > 0 && (
                <div className="mb-6">
                    <h4 className="font-semibold text-gray-900 mb-3 text-base">Recommendations</h4>
                    <div className="space-y-2">
                        {report.recommendations.map((rec, index) => (
                            <div key={index} className="flex items-start gap-3 p-3 bg-amber-50 rounded-lg border border-amber-200">
                                <span className="inline-block w-1.5 h-1.5 bg-amber-600 rounded-full mt-2 flex-shrink-0"></span>
                                <span className="text-gray-700 text-sm leading-relaxed">{rec}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

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
